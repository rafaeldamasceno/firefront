To install for using with The Platform, run:

```
apt-get install build-essential libnetcdf-cxx-legacy-dev
``` 

Then build a Python environment **using version 3.6 or lower** (I suggest using miniconda):

```
conda config --add channels conda-forge
conda config --set channel_priority strict
conda create -n firefrontenv python=3.6 scons pyproj numpy scipy pika pexpect
```

After installing the enviroment, activate it, navigate to the firefront folder and run:

```
scons
```

If it errors out, try cleaning the build `scons -c` and deleting the `.sconsign.dblite` file.

To run the middleware, it is expected for elevation and land class data to be in `tools/TerrainElevation/` and `tools/TerrainLandClass/`, respectively. The file `runways.csv` should be inside the `C:\FEUP` folder. The Platform's path should be adjusted in the `tools/server.py` file.

With all the needed files in place, run the middleware:

```
cd tools
python server.py
```


---

ForeFire has been designed and run on Unix systems, three modules can be built with the source code.

  - An interpreter (executable)
  - A dynamic library (shared, with C/C++/Java and Fortran bindings)

NetCDF  Library V3 or later must be installed on the system to build Forefire
Get it from http://www.unidata.ucar.edu/software/netcdf/

Compilation requires a c++ compiler, but it has only been tested on gcc/g++ compiler.
The SCons python tool is used to make the library and executable, get it from  http://www.scons.org
A sample SConstruct file is included with the distribution, try it and if it does not work, set the environment variables, edit it and insert the path to the Netcdf (and Java headers for JNI bindings if required).
NetCDF-C++ >>LEGACY<< is required for compatibilities issues, get it from :
https://www.unidata.ucar.edu/downloads/netcdf/netcdf-cxx/index.jsp

to run a real fire, go in Examples/aullene/ directory and  type "../../CommandShell -i aullene.ff" from the commandline

The "swig" repository contains python bindings requires numpy (and numpy.i), swig, and matplotlib for testing. 
