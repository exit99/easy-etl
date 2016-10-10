from setuptools import setup

if __name__ == '__main__':
    setup(
        name='easy-etl',
        version='0.3.2',
        author='Zach Kazanski',
        author_email='kazanski.zachary@gmail.com',
        description='A lightweight data cube pipeline for ETL processes in python.',
        url="https://github.com/kazanz/easy-etl",
        packages=['easy_etl'],
        include_package_data=True,
        install_requires=[
            'dataset==0.6.4',
            'tqdm==4.7.6',
        ],
        classifiers=[
            'Programming Language :: Python',
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: MIT License',
            'Natural Language :: English',
            'Operating System :: OS Independent',
            'Development Status :: 4 - Beta',
        ],
    )
