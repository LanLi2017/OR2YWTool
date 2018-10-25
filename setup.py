from setuptools import setup
setup(
  name = 'or2ywtool',
  packages = ['or2ywtool'],
  version = '0.0.2',
  description = 'OR2YW Tool',
  url = 'https://github.com/LanLi2017/OR2YWTool',
  classifiers=[  # Optional
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 3 - Alpha',

    # Indicate who your project is intended for
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',

    # Pick your license as you wish
    'License :: OSI Approved :: MIT License',

    # Specify the Python versions you support here. In particular, ensure
    # that you indicate whether you support Python 2, Python 3 or both.
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
  ],
  entry_points={
        'console_scripts': [
            'or2yw = or2ywtool.__main__:run'
        ],
    }
)
