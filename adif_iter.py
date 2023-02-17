###############################################################################
# adif_iter.py
# Author: Tom Kerr AB3GY
#
# adif_iter class.
# The adif_iter class provides an iterator to loop through all QSO records in 
# an ADIF file.
#
# ADIF = Amateur Data Interchange Format
# Reference: http://www.adif.org
#
# Designed for personal use by the author, but available to anyone under the
# license terms below.
###############################################################################

###############################################################################
# License
# Copyright (c) 2020 Tom Kerr AB3GY (ab3gy@arrl.net).
#
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice,   
# this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,  
# this list of conditions and the following disclaimer in the documentation 
# and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without 
# specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
###############################################################################

# System level packages.
import codecs
import os
import sys
import traceback


##############################################################################
# Local envrionment setup.
##############################################################################

from adif import adif
from strutils import format_date, format_time, make_utf8

scriptname = os.path.basename(sys.argv[0])


##############################################################################
# adif_iter class.
##############################################################################
class adif_iter(object):
    """
    adif_iter class.
    
    Provides an iterator to loop through all QSO records in an ADIF file.
    The iterator handles opening and closing the file.
    
    Input data is converted to UTF-8 encoding; data that cannot be converted
    to UTF-8 is ignored and dropped.
    """

    # ------------------------------------------------------------------------
    def __init__(self, filename):
        """
        Class constructor.
        Must provide an ADIF filename for initialization.
        """
        self.adifobj = adif()
        self.filename = filename
        self.fileobj = None

    # ------------------------------------------------------------------------
    def __iter__(self):
        """
        Initializes the iterator.
        """
        (status, errmsg) = self.open()
        return self

    # ------------------------------------------------------------------------
    def __next__(self):
        """
        Computes and returns the next file in the sequence.
        Raises the StopIteration exception when complete.
        """
        qso = {}
        status = False
        errmsg = ''
        (qso, status, errmsg) = self.next_qso()
        if status:
            if (len(qso) > 0):
                return qso
            else:
                self.close()
                raise StopIteration
        else:
            self.close()
            raise StopIteration

    # ----------------------------------------------------------------------------    
    def _print_msg(self, msg):
        """
        Print a formatted message.  Used internally for printing error messages.

        Parameters
        ----------
        msg : str
            The message text to print.
        
        Returns
        -------
        None
        """
        cl = type(self).__name__                         # This class name
        fn = str(traceback.extract_stack(None, 2)[0][2]) # Calling function name
        print(cl + '.' + fn + ': ' + msg)

    # ------------------------------------------------------------------------
    def open(self):
        """
        Opens the ADIF file for reading.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        (status, errmsg) : tuple
            status : bool
                True if the file opened successfully, False otherwise.
            errmsg : str
                The file open error message if an error occurred.
        """
        status = False
        errmsg = ''
        if self.fileobj is not None:
            self.close()
        try:
            self.fileobj = codecs.open(self.filename, mode='r', encoding='utf-8', errors='ignore')
            status = True
        except Exception as err:
            self.fileobj = None
            errmsg = str(err)
            self._print_msg(errmsg)
        return (status, errmsg)

    # ------------------------------------------------------------------------
    def close(self):
        """
        Closes the ADIF file.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None
        """
        if self.fileobj is not None:
            try:
                fileobj.close()
            except Exception as err:
                pass
            self.fileobj = None

    # ------------------------------------------------------------------------
    def all_qsos(self):
        """
        The iterator function to use in a for() loop.
        
        Parameters
        ----------
        None
        
        Returns
        -------
        qso : dict
            The next QSO record as a Python dictionary.
        
        Example usage:
            myAdifIter = adif_iter(filename)
            for qso in myAdifIter.all_qsos():
                myAdif = adif(qso)
                do_stuff()
        """
        return iter(self)

    # ------------------------------------------------------------------------
    def next_qso(self):
        """
        Method to get the next QSO record from an open ADIF file.
    
        Parameters
        ----------
        None
        
        Returns
        -------
        (qso, status, errmsg) : tuple
            qso : dict
                The QSO record as a Python dictionary.  Returns an empty
                dictionary when no records are left.
            status : bool
                True if the record was retrieved successfully, False otherwise.  
            errmsg : str
                The error message if an error occurred.
        """
        qso = {}
        status = False
        errmsg = ''
        
        if self.fileobj is not None:
            try:
                status = self.adifobj.next_record(self.fileobj)
                if status:
                    qso = self.adifobj.get_record()
            except Exception as err:
                status = False
                errmsg = str(err)
                self._print_msg(errmsg)
                qso = self.adifobj.get_record()
        
        return (qso, status, errmsg)


##############################################################################
# Main program.
############################################################################## 
if __name__ == "__main__":

    if (len(sys.argv) < 2):
        print('Usage:', scriptname, '<ADIF-file>')
        sys.exit(1)
    
    qso_count = 0
    
    # Instantiate an adif_iter object with an ADIF file.
    myAdifFile = adif_iter(sys.argv[1])
    
    # Iterate through all QSOs in the ADIF file.
    for qso in myAdifFile.all_qsos():
        qso_count += 1
        myAdif = adif(qso)
        print(myAdif.get_field('CALL'), \
            myAdif.get_field('BAND'), \
            myAdif.get_field('MODE'), \
            format_date(myAdif.get_field('QSO_DATE')), \
            format_time(myAdif.get_field('TIME_ON')))
        
    print(str(qso_count), 'QSOs found.')
   