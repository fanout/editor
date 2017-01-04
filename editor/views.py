import json
import urlparse
from django.db import transaction, IntegrityError
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from gripcontrol import HttpStreamFormat
from django_grip import publish
from text_operation import TextOperation
from models import User, Document, DocumentChange

def _doc_get_or_create(eid):
	try:
		doc = Document.objects.get(eid=eid)
	except Document.DoesNotExist:
		try:
			doc = Document(eid=eid)
			doc.save()
		except IntegrityError:
			doc = Document.objects.get(eid=eid)
	return doc

def index(request, document_id=None):
	if not document_id:
		document_id = 'default'
	base_url = '%s://%s%s' % (
		'https' if request.is_secure() else 'http',
		request.META.get('HTTP_HOST') or 'localhost',
		reverse('index-default'))
	if base_url.endswith('/'):
		base_url = base_url[:-1]
	context = {
		'document_id': document_id,
		'base_url': base_url
	}
	return render(request, 'editor/index.html', context)

def users(request):
	if request.method == 'POST':
		name = request.POST['name']
		try:
			user = User.objects.get(name=name)
		except User.DoesNotExist:
			try:
				user = User(name=name)
				user.save()
			except IntegrityError:
				user = User.objects.get(name=name)
		return JsonResponse(user.export())
	else:
		return HttpResponseNotAllowed(['POST'])

def user(request, user_id):
	if request.method == 'GET':
		user = get_object_or_404(User, id=user_id)
		return JsonResponse(user.export())
	else:
		return HttpResponseNotAllowed(['GET'])

def document(request, document_id):
	if request.method == 'GET':
		try:
			doc = Document.objects.get(eid=document_id)
		except Document.DoesNotExist:
			doc = Document(eid=document_id)
		return JsonResponse(doc.export())
	else:
		return HttpResponseNotAllowed(['GET'])

def document_changes(request, document_id):
	if request.method == 'GET':
		sse = False
		if request.GET.get('sse') == 'true':
			sse = True
		else:
			accept = request.META.get('HTTP_ACCEPT')
			if accept and accept.find('text/event-stream') != -1:
				sse = True

		after = None

		grip_last = request.META.get('HTTP_GRIP_LAST')
		if grip_last:
			at = grip_last.find('last-id=')
			if at == -1:
				raise ValueError('invalid Grip-Last header')
			at += 8
			after = int(grip_last[at:])

		if after is None and sse:
			last_id = request.META.get('Last-Event-ID')
			if last_id:
				after = int(last_id)

		if after is None and sse:
			last_id = request.GET.get('lastEventId')
			if last_id:
				after = int(last_id)

		if after is None:
			afterstr = request.GET.get('after')
			if afterstr:
				after = int(afterstr)

		try:
			doc = Document.objects.get(eid=document_id)
			if after is not None:
				if after > doc.version:
					raise ValueError('version in the future')
				changes = DocumentChange.objects.filter(
					document=doc,
					version__gt=after).order_by('version')[:50]
				out = [c.export() for c in changes]
				if len(out) > 0:
					last_version = out[-1]['version']
				else:
					last_version = after
			else:
				out = []
				last_version = doc.version
		except Document.DoesNotExist:
			if after is not None and after > 0:
				raise ValueError('version in the future')
			out = []
			last_version = 0

		if sse:
			body = ''
			for i in out:
				event = 'id: %d\nevent: change\ndata: %s\n\n' % (
					i['version'], json.dumps(i))
				body += event
			resp = HttpResponse(body, content_type='text/event-stream')
			parsed = urlparse.urlparse(reverse('document-changes', args=[document_id]))
			resp['Grip-Link'] = '<%s?sse=true&after=%d>; rel=next' % (
				parsed.path, last_version)
			if len(out) < 50:
				resp['Grip-Hold'] = 'stream'
				resp['Grip-Channel'] = 'document-%s; prev-id=%s' % (
					document_id, last_version)
			return resp
		else:
			return JsonResponse({'changes': out})
	elif request.method == 'POST':
		opdata = json.loads(request.POST['op'])
		for i in opdata:
			if not isinstance(i, int) and not isinstance(i, basestring):
				raise ValueError('invalid operation')

		op = TextOperation(opdata)

		request_id = request.POST['request-id']
		parent_version = int(request.POST['parent-version'])
		doc = _doc_get_or_create(document_id)

		saved = False
		with transaction.atomic():
			doc = Document.objects.select_for_update().get(id=doc.id)
			try:
				# already submitted?
				c = DocumentChange.objects.get(
					document=doc,
					request_id=request_id,
					parent_version=parent_version)
			except DocumentChange.DoesNotExist:
				changes_since = DocumentChange.objects.filter(
					document=doc,
					version__gt=parent_version,
					version__lte=doc.version).order_by('version')

				for c in changes_since:
					op2 = TextOperation(json.loads(c.data))
					op, _ = TextOperation.transform(op, op2)

				next_version = doc.version + 1
				c = DocumentChange(
					document=doc,
					version=next_version,
					request_id=request_id,
					parent_version=parent_version,
					data=json.dumps(op.ops))
				c.save()
				doc.content = op(doc.content)
				doc.version = next_version
				doc.save()
				saved = True

		if saved:
			event = 'id: %d\nevent: change\ndata: %s\n\n' % (
				c.version, json.dumps(c.export()))
			publish(
				'document-%s' % document_id,
				HttpStreamFormat(event),
				id=str(c.version),
				prev_id=str(c.version - 1))

		return JsonResponse({'version': c.version})
	else:
		return HttpResponseNotAllowed(['GET', 'POST'])
