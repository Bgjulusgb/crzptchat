from setuptools import setup, find_packages

setup(
    name='secure-chat',
    version='1.0.0',
    description='A secure, end-to-end encrypted messaging platform',
    author='SecureChat Team',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[
        'cryptography>=41.0.0',
        'PyJWT>=2.8.0',
        'bcrypt>=4.0.0',
        'python-dotenv>=1.0.0',
        'SQLAlchemy>=2.0.0',
        'Flask>=2.3.0',
        'Werkzeug>=2.3.0',
        'Flask-SQLAlchemy>=3.0.0',
        'Flask-JWT-Extended>=4.5.0',
        'Flask-Cors>=4.0.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
            'black>=23.7.0',
            'flake8>=6.0.0',
            'mypy>=1.5.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'secure-chat-cli=secure_chat_app:main',
            'secure-chat-web=secure_chat.web.app:main',
        ],
    },
)