import json
from django.db import transaction, IntegrityError
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404
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
		accept = request.META.get('HTTP_ACCEPT')
		if accept and accept.find('text/event-stream') != -1:
			sse = True
			last_id = request.META.get('Last-Event-ID')
			if not last_id:
				last_id = request.GET.get('lastEventId')
				if not last_id:
					last_id = request.GET.get('after')
					if not last_id:
						raise ValueError(
							'client must include last event id or after')
			after = int(last_id)
		else:
			after = int(request.GET['after'])

		try:
			doc = Document.objects.get(eid=document_id)
			changes = DocumentChange.objects.filter(
				document=doc,
				version__gt=after).order_by('version')[:100]
			out = [c.export() for c in changes]
		except Document.DoesNotExist:
			out = []

		if sse:
			body = ''
			for i in out:
				body += 'event: change\nid: %d\ndata: %s\n\n' % (i['version'], json.dumps(i))
			return HttpResponse(body, content_type='text/event-stream')
		else:
			return JsonResponse({'changes': out})
	elif request.method == 'POST':
		opdata = json.loads(request.POST['op'])
		for i in opdata:
			if not isinstance(i, int) and not isinstance(i, basestring):
				raise ValueError('invalid operation')

		op = TextOperation(opdata)

		user = get_object_or_404(User, id=request.POST['user'])
		parent_version = int(request.POST['parent-version'])
		doc = _doc_get_or_create(document_id)

		with transaction.atomic():
			doc = Document.objects.select_for_update().get(id=doc.id)
			try:
				# already submitted?
				c = DocumentChange.objects.get(
					document=doc,
					author=user,
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
					author=user,
					parent_version=parent_version,
					data=json.dumps(op.ops))
				c.save()
				doc.content = op(doc.content)
				doc.version = next_version
				doc.save()

		return JsonResponse({'id': c.version})
	else:
		return HttpResponseNotAllowed(['GET', 'POST'])
