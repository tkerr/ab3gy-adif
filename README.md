# AB3GY ADIF Utilities 
A set of Python classes used to manipulate ADIF records.
Developed for personal use by the author, but available to anyone under the license terms below.

ADIF = Amateur Data Interchange Format
Reference: http://www.adif.org

Developed for personal use by the author, but available to anyone under the license terms below.

## adif.py
The `adif` class provides an easy way to parse and manipulate ADIF QSO records.

The `adifMerge` class provides methods to match ADIF records and to merge one ADIF record into another.

The `qslrcvd` class provides methods for determining QSL received status from ADIF records. It works with ADIF QSO/QSL records from ARRL LoTW, Club Log, eQSL.cc and QRZ.com.

## adif_iter.py
The `adif_iter` class provides an iterator to loop through all QSO records in an ADIF file.

## Dependencies
Written for Python 3.x.

The `adif` class uses the `make_utf8` function in strutils.py.

Repository: https://github.com/tkerr/ab3gy-pyutils
 
## Author
Tom Kerr AB3GY
ab3gy@arrl.net

## License
Released under the 3-clause BSD license.
See license.txt for details.
