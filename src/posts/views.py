from django.shortcuts import render,get_object_or_404
from django.http import HttpResponse,HttpResponseRedirect,Http404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.db.models import Q,F
from django.core.paginator import Paginator
from django.utils import timezone
from faker import Faker
import logging
import logging.config

from .models import Post
from .forms import PostForm

from comments.models import Comment
from comments.forms import CommentForm


# Create your views here.

logging.config.fileConfig(fname='logs/log.conf')
logger = logging.getLogger('posts')

def post_index(request,slug = None):
    qs_list = Post.objects.all()
    logger.info(f'{qs_list.count()} posts listed.')
    if slug is not None:
        qs_list = Post.objects.filter(category__icontains=slug)
    query = request.GET.get("q")
    if query:
        qs_list = qs_list.filter(
            Q(title__icontains=query)|
            Q(content__icontains=query)|
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        ).distinct()
    paginator = Paginator(qs_list, 4)
    page_request_var = 'page'
    page_number = request.GET.get(page_request_var)
    page_obj = paginator.get_page(page_number)
    context = {'queryset':page_obj,'title':'List of Posts','page_request_var':page_request_var}
    return render(request,template_name='posts/index.html',context=context)

def post_create(request):
    if not request.user.is_authenticated:
        logger.error(f'Not Authenticated')
        return HttpResponse('You are not authenticated')
    form = PostForm(request.POST or None,request.FILES or None)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.user = request.user
        instance.save()
        logger.info(f'Post created by {request.user} with title {instance.title}')
        messages.success(request,'Post created. ')
        return HttpResponseRedirect(instance.get_absolute_url())
    context = {'form':form}
    return render(request,template_name='posts/create.html',context=context)

def post_list(request):
    if not request.user.is_authenticated:
        logger.error(f'Not Authenticated')
        return HttpResponse('You are not authenticated')
    qs_list = Post.objects.filter(user=request.user)
    logger.info(f'{request.user} listed {qs_list.count()} posts.')
    query = request.GET.get("q")
    if query:
        qs_list = qs_list.filter(
            Q(title__icontains=query)|
            Q(content__icontains=query)|
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        ).distinct()
    paginator = Paginator(qs_list, 5)
    page_request_var = 'page'
    page_number = request.GET.get(page_request_var)
    page_obj = paginator.get_page(page_number)
    context = {'queryset':page_obj,'title':'List of Posts','page_request_var':page_request_var}
    return render(request,template_name='posts/list.html',context=context)

def post_details(request,slug=None):
    queryset = Post.objects.filter(slug=slug)
    if not queryset.exists():
        Http404
    qs_details = queryset[0]
    if qs_details.draft or qs_details.publish > timezone.now().date():
        Http404
    if not request.user.is_authenticated:
        return HttpResponse('You are not authenticated')
    if request.method == 'GET':
        queryset.update(views_count = F('views_count') + 1)
    qs_details.refresh_from_db()

    category = qs_details.category
    print(category)
    queryset_category = Post.objects.filter(category=category).order_by("-views_count")
    if queryset_category.count() > 3:
        queryset_category = queryset_category[:3]

    initial_data = {'content_type':qs_details.get_content_type,'object_id':qs_details.id}
    form = CommentForm(request.POST or None,initial=initial_data)
    if form.is_valid():
        c_type = form.cleaned_data.get("content_type")
        app_label,model_label = c_type.split('|')
        content_type = ContentType.objects.get(app_label__iexact=app_label.strip(), model__iexact=model_label.strip())
        obj_id = form.cleaned_data.get('object_id')
        content_data = form.cleaned_data.get("content")
        parent_obj = None
        try:
            parent_id = int(request.POST.get('parent_id'))
        except:
            parent_id = None
        
        if parent_id:
            parent_qs = Comment.objects.filter(id=parent_id)
            if parent_qs.exists() and parent_qs.count() == 1:
                parent_obj = parent_qs.first()

        new_comment,created = Comment.objects.get_or_create(
                                    user = request.user,
                                    content_type = content_type,
                                    object_id = obj_id,
                                    content =content_data,
                                    parent = parent_obj,
        )
        logger.info(f'{request.user} commented {new_comment.content}.')
        return HttpResponseRedirect(new_comment.content_object.get_absolute_url())

    comments = qs_details.comment
    context = {'query':qs_details,'title':qs_details.title,'comments':comments,'comment_form':form,'queryset_category':queryset_category}
    return render(request,template_name='posts/details.html',context=context)

def post_update(request,slug=None):
    if not request.user.is_authenticated:
        return HttpResponse('You are not authenticated')
    qs_update = get_object_or_404(Post,slug=slug)
    form = PostForm(request.POST or None,request.FILES or None,instance=qs_update)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.save()
        logger.info(f'{request.user} updated {instance.title}.')
        return HttpResponseRedirect(instance.get_absolute_url())
    context = {'query':qs_update,'title':qs_update.title,'form':form}
    return render(request,template_name='posts/edit.html',context=context)

def post_delete(request,slug=None):
    try:
        qs_delete = get_object_or_404(Post,slug=slug)
    except:
        raise Http404('This is not present')

    if not request.user.is_authenticated:
        return HttpResponse('You are not authenticated')

    if qs_delete.user != request.user:
        response = HttpResponse("you dont have permission to view this.")
        response.status_code = 403
        return response

    if request.method == 'POST':
        qs_delete.delete()
        logger.info(f'{request.user} deleted {qs_delete}.')
        messages.success(request,'Post has been deleted')
        return HttpResponseRedirect(reverse('posts:postlist'))

    context = {'qs_delete':qs_delete}
    return render(request,'posts/post_delete.html',context=context)

def contact(request):
    return render(request,template_name='posts/contact.html')
    