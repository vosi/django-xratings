from setuptools import setup

kwargs = {
    'name': 'django-xratings',
    'version': ".".join(map(str, __import__('xratings').__version__)),
    'description': 'Django ratings system.',
    'author': 'Tartynskyi Volodymyr',
    'author_email': 'fon.vosi@gmail.com',
    'url': 'https://github.com/vosi/django-xratings',
    'keywords': 'django,ratings',
    'license': 'BSD',
    'packages': ['xratings',],
    'include_package_data': True,
    'install_requires': ['setuptools'],
    'zip_safe': False,
    'classifiers': [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
}
setup(**kwargs)
