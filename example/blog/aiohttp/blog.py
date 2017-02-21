"""Blog application using aiohttp and pymodm with motor_asyncio driver."""
import asyncio
import datetime
import functools
import os.path

import aiohttp_jinja2
import aiohttp_session
import jinja2

import blog_models

from aiohttp import web

from bson import ObjectId
from pymodm_motor.errors import ValidationError
from pymongo.errors import DuplicateKeyError

from pymodm_motor import connect, MOTOR_ASYNCIO_DRIVER
from pymodm_motor.dereference import dereference

from blog_models import User, Post, Comment


async def init_app(loop):
    """Initialize aiohttp web application."""
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

    # Establish a connection to the database.
    connect('mongodb://localhost:27017/blog',
            mongo_driver=MOTOR_ASYNCIO_DRIVER, io_loop=loop)
    # pymodm_motor does not create indexes automatically as pymodm does.
    # Use MotorModel.objects.create_indexes() coroutine to create
    # models' indexes explicitly. Application initialization is
    # a good place to do that.
    await blog_models.create_indexes()
    # Create application
    app = web.Application(debug=True, loop=loop)

    # setup jinja2 templates
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(os.path.join(APP_DIR, 'templates')))
    aiohttp_jinja2.get_env(app).filters['human_date'] = human_date

    # setup session
    # SimpleCookieStorage is only for demo
    # it's very non-secure, don't use this storage for real app
    aiohttp_session.setup(
        app,
        aiohttp_session.SimpleCookieStorage())

    # add routes
    app.router.add_get('/', index, name='index')
    app.router.add_get('/login', login, name='login')
    app.router.add_post('/login', login)
    app.router.add_get('/logout', logout, name='logout')
    app.router.add_get('/users/new', new_user, name='new_user')
    app.router.add_post('/users/new', new_user)
    app.router.add_get('/posts/new', create_post, name='create_post')
    app.router.add_post('/posts/new', create_post)
    app.router.add_get('/posts/{post_id}', get_post, name='get_post')
    app.router.add_post('/comments/new', new_comment, name='new_comment')

    # add static route
    # this is only for demo, use web servers to handle static
    app.router.add_static(prefix='/static/',
                          path=os.path.join(APP_DIR, 'static'))

    return app


def human_date(value, format="%B %d at %I:%M %p"):
    """Format a datetime object to be human-readable in a template."""
    return value.strftime(format)


def logged_in(func):
    """Decorator that redirects to login page if a user is not logged in."""
    @functools.wraps(func)
    async def wrapper(*args):
        request = args[-1]
        session = await aiohttp_session.get_session(request)
        if 'user' not in session:
            raise web.HTTPFound(request.app.router['login'].url_for())
        return await func(*args)

    return wrapper


@logged_in
@aiohttp_jinja2.template('new_post.html')
async def create_post(request):
    if request.method == 'GET':
        # return context for template
        return {}
    else:
        session = await aiohttp_session.get_session(request)
        form = await request.post()
        if form['date']:
            post_date = form['date']
        else:
            post_date = datetime.datetime.now()
        try:
            await Post(
                title=form['title'],
                date=post_date,
                body=form['content'],
                author=session['user']).save()
        except ValidationError as exc:
            return {
                'errors': exc.message
            }

        # raise redirect response to avoid template decorator
        raise web.HTTPFound(request.app.router['index'].url_for())


@aiohttp_jinja2.template('login.html')
async def login(request):
    if request.method == 'GET':
        # Return context for login form.
        return {}
    else:
        # Login.
        session = await aiohttp_session.get_session(request)
        form = await request.post()
        email, password = form['email'], form['password']
        try:
            # Note: logging users in like this is acceptable for demonstration
            # projects only.
            user = await User.objects.get(
                {'_id': email, 'password': password})
        except User.DoesNotExist:
            return {
                'error': 'Bad email or password'
            }

        # Store user in the session.
        session['user'] = user.email

        # raise redirect response to avoid template decorator
        raise web.HTTPFound(request.app.router['index'].url_for())


async def logout(request):
    session = await aiohttp_session.get_session(request)
    session.pop('user', None)
    # store flash message between requests
    session['flash'] = 'You have been successfully logged out.'
    return web.HTTPFound(request.app.router['index'].url_for())


@aiohttp_jinja2.template('new_user.html')
async def new_user(request):
    if request.method == 'GET':
        return {}
    else:
        form = await request.post()
        try:
            # Note: real applications should handle user registration more
            # securely than this.
            # Use `force_insert` so that we get a DuplicateKeyError if
            # another user already exists with the same email address.
            # Without this option, we will update (replace) the user with
            # the same id (email).
            await User(
                email=form['email'],
                handle=form['handle'],
                password=form['password']).save(force_insert=True)
        except ValidationError as ve:
            return {
                'errors': ve.message
            }
        except DuplicateKeyError:
            # Email address must be unique.
            return {
                'errors': {
                    'email': [
                        'There is already a user with that email address.'
                    ]
                }
            }

    # raise redirect response to avoid template decorator
    raise web.HTTPFound(request.app.router['index'].url_for())


@aiohttp_jinja2.template('index.html')
async def index(request):
    session = await aiohttp_session.get_session(request)
    # restore flash message if any
    flash = session.pop('flash', None)
    flashed_messages = [flash] if flash else []

    # Use a list here so we can do "if posts" efficiently in the template.
    # Note that pymodm_motor queryset cannot return iterator
    # but asynchronous iterator (to use with async for) or
    # asynchronous generator (for python version >= 3.6)
    # >> posts = Post.objects.all().to_list()
    # is equivalent to:
    # >> posts = list()
    # >> async for item in Post.objects.all():
    # >>     posts.append(item)
    # And with python version >= 3.6 you can use asynchronous comprehensions
    # >> posts = [item async for item in Posts.objects.all()]
    return {
        'posts': await Post.objects.all().to_list(dereference=True),
        'session': session,
        'flashed_messages': flashed_messages
    }


async def get_post(request):
    post_id = request.match_info['post_id']
    try:
        # `post_id` is a string, but it's stored as an ObjectId in the db.
        # Note that auto_dereference is off for pymodm_motoro models and
        # dereference should be used explicitly
        post = await dereference(
            await Post.objects.get({'_id': ObjectId(post_id)}))
    except Post.DoesNotExist:
        response = web.HTTPNotFound(
            text=aiohttp_jinja2.render_string('404.html', request, {}))
        response.content_type = 'text/html'
        return response

    return aiohttp_jinja2.render_template(
        'post.html', request, {'post': post})


@aiohttp_jinja2.template('post.html')
async def new_comment(request):
    session = await aiohttp_session.get_session(request)
    form = await request.post()
    post_id = ObjectId(form['post_id'])
    try:
        post = await dereference(
            await Post.objects.get({'_id': post_id}))
    except Post.DoesNotExist:
        session['flash'] = 'No post with id: %s' % post_id
        raise web.HTTPFound(request.app.router['index'].url_for())

    comment = Comment(
        author=form['author'],
        date=datetime.datetime.now(),
        body=form['content'])
    post.comments.append(comment)
    try:
        await post.save()
    except ValidationError as e:
        post.comments.pop()
        comment_errors = e.message['comments'][-1]

        return {
            'post': post,
            'errors': comment_errors
        }

    return {
        'post': post,
        'flashed_messages': ['Comment saved successfully.']
    }


def main():
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app(loop))
    web.run_app(app, host='127.0.0.1', port=5000)


if __name__ == '__main__':
    main()
