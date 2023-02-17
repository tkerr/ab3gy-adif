###############################################################################
# adif.py
# Author: Tom Kerr AB3GY
#
# Classes used to manipulate ADIF records using Python dictionaries.
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

from datetime import datetime, timedelta
import re
import sys
import traceback

# Local packages.
from strutils import make_utf8


##############################################################################
# Compiled regular expressions used for parsing.
# For the specifier:
#     Tag is contained in parentheses and is returned as match group 1
#     Field length is contained in parentheses and is returned as match group 2
#     Field type is contained in parentheses and is returned as match group 3
#     Field value is contained in parentheses and is returned as match group 4
# The field value can be extracted from group 4 using the field length as follows:
#     length = int(match.group(2))
#     value  = match.group(4)[0:length]
##############################################################################
adif_specifier_re = re.compile('\<(\w+):(\d+)(:\w)?\>([^<]*)', re.IGNORECASE)
adif_eoh_re       = re.compile("\<EOH\>", re.IGNORECASE)
adif_eor_re       = re.compile("\<EOR\>", re.IGNORECASE)


##############################################################################
# Lists for frequency-to-band conversion.
##############################################################################

bandmap_freqs = [0.1357, 0.1378, 0.472, 0.479, 0.501, 0.504, 1.8, 2.0, 
    3.5, 4.0, 5.06, 5.45, 7.0, 7.3, 10.1, 10.15, 14.0, 14.35, 18.068, 18.168, 
    21.0, 21.45, 24.890, 24.99, 28.0, 29.7, 50.0, 54.0, 70.0, 71.0, 144.0, 148.0,
    222.0, 225.0, 420.0, 450.0, 902.0, 928.0, 1240.0, 1300.0, 2300.0, 2450.0, 
    3300.0, 3500.0, 5650.0, 5925.0, 10000.0, 10500.0, 24000.0, 24250.0, 
    47000.0, 47200.0, 75500.0, 81000.0, 119980.0, 120020.0, 142000.0, 149000.0,
    241000.0, 250000.0]
    
bandmap_bands = ['2190m', '2190m', '630m', '630m', '560m', '560m', '160m', '160m',
    '80m', '80m', '60m', '60m', '40m', '40m', '30m', '30m', '20m', '20m', '17m', '17m',
    '15m', '15m', '12m', '12m', '10m', '10m', '6m', '6m', '4m', '4m', '2m', '2m',
    '1.25m', '1.25m', '70cm', '70cm', '33cm', '33cm', '23cm', '23cm', '13cm', '13cm',
    '9cm', '9cm', '6cm', '6cm', '3cm', '3cm', '1.25cm', '1.25cm', 
    '6mm', '6mm', '4mm', '4mm', '2.5mm', '2.5mm', '2mm', '2mm',
    '1mm', '1mm']


##############################################################################
# Functions.
##############################################################################

def freq2band(fmhz):
    """
    Convert frequency in MHz to its respective band.
    """
    max = len(bandmap_freqs) - 1
    if (fmhz < bandmap_freqs[0]): return 'NONE'
    if (fmhz > bandmap_freqs[max]): return 'NONE'
    for i in range(0, max, 2):
        if (fmhz >= bandmap_freqs[i]) and (fmhz <= bandmap_freqs[i+1]):
            return bandmap_bands[i]
    return 'NONE'
    


##############################################################################
# ADIF class.
##############################################################################
class adif(object):
    """
    A class for parsing ADIF QSO records.
    """

    # ------------------------------------------------------------------------
    def __init__(self, dict=None):
        """
        Class constructor.
        """
        # Variable initialization.
        self.__version__ = str('0.1')  # Version per PEP 396
        
        # QSO record fields stored as a dictionary of strings.
        self.QSO = {}
        
        # Header record fields stored as a dictionary of strings.
        self.HEADER = {}
        
        # End of header detected flag.
        self._EOH = False
        
        # Initialize from supplied dictionary.
        if dict is not None:
            self.QSO = dict

        # Remainder of the last line read from the ADIF input file.
        self._line = ''
        

    # ------------------------------------------------------------------------    
    def clear(self):
        """
        Clear all ADIF record fields.
        """
        self.QSO = {}
        self._line = ''

    # ------------------------------------------------------------------------ 
    def copy_from(self, adif):
        """
        Copy from another adif object.
        """
        self.clear()
        self.QSO = adif.QSO
        self.HEADER = adif.HEADER
        self._line = adif._line

    # ------------------------------------------------------------------------    
    def del_field(self, field):
        """
        Delete the specified ADIF QSO field.
        Has no effect if field does not exist.
        """
        field = field.strip().upper()
        if field in self.QSO.keys():
            del self.QSO[field]

    # ------------------------------------------------------------------------    
    def eoh(self):
        """
        Return True if EOH was found in the last parsed line, or False otherwise.
        """
        return self._EOH

    # ------------------------------------------------------------------------    
    def get_adif(self):
        """
        Return the entire ADIF QSO record as a formatted ADIF record.
        """
        adif = ""
        for field in sorted(self.QSO.keys()):
            value = self.QSO[field]
            adif += '<' + field + ':' + str(len(value)) + '>' + value + ' '
        adif += '<EOR>'
        return adif

    # ------------------------------------------------------------------------    
    def get_field(self, field):
        """
        Return the specified ADIF QSO field.
        Returns an empty string if not found.
        """
        value = ""
        field = field.strip().upper()
        if field in self.QSO.keys():
            value = self.QSO[field]
        return value

    # ------------------------------------------------------------------------    
    def get_field_names(self):
        """
        Return a list of all fields in the record.
        """
        #return self.QSO.keys() # Returns an iterator - not desired
        return list(self.QSO)   # Forces a list to be returned

    # ------------------------------------------------------------------------    
    def get_header(self):
        """
        Return all header fields as a single string with newlines after each field.
        """
        hdr = ""
        for field in sorted(self.HEADER.keys()):
            value = self.HEADER[field]
            hdr += '<' + field + ':' + str(len(value)) + '>' + value + '\n'
        return hdr

    # ------------------------------------------------------------------------    
    def get_record(self):
        """
        Return the entire ADIF QSO record as a dictionary.
        """
        return self.QSO

    # ------------------------------------------------------------------------    
    def has_field(self, field):
        """
        Return True if the field is contained in the record, or False otherwise.
        """
        field = field.strip().upper()
        if field in self.get_field_names():
            return True
        return False

    # ------------------------------------------------------------------------    
    def next_record(self, file):
        """
        Get the next ADIF record in an open file.
        
        Returns True if a record was parsed successfully, or False otherwise.
        
        LIMITATION: Multiple-line fields are converted to a single line.
        Newline characters are replaced with spaces.
        """
        eor = True # This clears the ADIF record upon first entry into self.parse() in the for() loop
        
        # Check if there is an <EOR> in the current line.
        m = adif_eor_re.search(self._line)
        if m: 
            # The current line contains an <EOR>. Parse it.
            eor = self.parse(self._line, True);
            if eor:
                idx = m.end()    # Index of the end of the <EOR> in the string
                self._line = self._line[idx:] # Remove the part we just parsed
                return True
        
        # Get lines in the file until an <EOR> is found.
        # Convert multiple lines to a single line.
        for line in file:
            self._line += make_utf8(line).replace('\n', ' ').replace('\r', ' ')  # Replace CR/LF with spaces
            
            # Check for end of header first.
            m = adif_eoh_re.search(self._line)
            if m:
                # Parse the header.
                self.parse(self._line, True);
                idx = m.end()    # Index of the end of the <EOH> in the string
                self._line = self._line[idx:] # Remove the part we just parsed
                eor = False
            
            m = adif_eor_re.search(self._line)
            if m:
                # End of record found.
                eor = self.parse(self._line, eor);
                if eor:
                    idx = m.end()    # Index of the end of the <EOR> in the string
                    self._line = self._line[idx:] # Remove the part we just parsed
                    return True

        # Check whatever is remaining at the end of the current line.
        m = adif_eor_re.search(self._line)
        if m:
            eor = self.parse(self._line, eor)
            if eor:
                idx = m.end()    # Index of the end of the <EOR> in the string
                self._line = self._line[idx:] # Remove the part we just parsed
                return True
                
        return False

    # ------------------------------------------------------------------------        
    def parse(self, record, new=False):
        """
        Parse an ADIF QSO record.
        The record is assumed to be properly formatted.
        Clears the record first if new = True
        
        Returns True if an End-Of-Record tag is found, False otherwise.
        
        LIMITATION: Multi-line fields are not supported by this function.
        The next_record() function will combine multi-line fields into a
        single line before calling this function.
        """
        self._EOH = False
        
        eor_found = False
        if new: self.clear()
        
        value = ''
        
        m = adif_specifier_re.search(record)
        while m:
            tag = m.group(1).upper()   # Group 1 is the ADIF tag
            sz  = int(m.group(2))      # Group 2 is the specified field length
            sz1 = len(m.group(4))      # Get the actual length of the field value
            if (sz1 < sz): sz = sz1    # Use the smaller length; non-UTF-8 chars can mess up the ADIF-specified length
            value = m.group(4)[0:sz]   # Group 4 is the field value
            self.QSO[tag] = value
            
            pos = int(m.start(4) + sz)
            record = record[pos:]
            m = adif_specifier_re.search(record)
            
            # Check for header-specific fields.
            if tag == 'ADIF_VER':
                self.HEADER[tag] = value
            elif tag == 'ADIF_VERS':            # Bug in Log4OM
                self.HEADER[tag] = value
                self.HEADER['ADIF_VER'] = value # ADIF standard tag name
            elif tag == 'CREATED_TIMESTAMP':
                self.HEADER[tag] = value
            elif tag == 'PROGRAMID':
                self.HEADER[tag] = value
            elif tag == 'PROGRAMVERSION':
                self.HEADER[tag] = value
            elif tag.startswith('USERDEF'):
                self.HEADER[tag] = value
        
        # Check for end of record.
        m = adif_eor_re.search(record)
        if m: eor_found = True
        
        # Check for end of header.
        m = adif_eoh_re.search(record)
        if m:
            self.clear()
            self._EOH = True
        
        return eor_found

    # ------------------------------------------------------------------------    
    def set_field(self, field, value):
        """
        Add the specified QSO field to the record.
        No checks are performed on the field or the data.
        """
        field = field.strip().upper()
        self.QSO[field] = value    


###############################################################################
# ADIF merge class.
###############################################################################
class adifMerge(object):
    """
    A class for merging two ADIF QSO records.
    """
    
    # ------------------------------------------------------------------------
    def __init__(self):
        """
        Class constructor.
        """
        # Variable initialization.
        self.__version__ = str("0.1")  # Version per PEP 396
        self.MaxSeconds  = 900         # Maximum time difference in seconds for a QSO match
        self.Verbose     = False       # Verbose debug printing if true

    # ----------------------------------------------------------------------------    
    def _print_msg(self, msg):
        """
        Print a formatted message.  Used internally for verbose printing.

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

    # -----------------------------------------------------------------------------
    def match(self, record1, record2):
        """
        Determine if two QSO records match.
        Call, band, mode must match exactly.
        QSO date/time must be within the maximum seconds specified in the
        MaxSeconds class variable.
        
        Parameters
        ----------
        record1 : dict
            An ADIF QSO record passed as a Python dictionary.
        record2 : dict
            An ADIF QSO record passed as a Python dictionary.
        
        Returns
        -------
        bool : True if records match, False otherwise.
        """
        match = False
        a1 = adif(record1)
        a2 = adif(record2)
        
        if (not self.minimumQso(record1)): 
            if self.Verbose:
                self._print_msg('Record 1 minimum QSO failed.')
            return False
        if (not self.minimumQso(record2)):
            if self.Verbose:
                self._print_msg('Record 2 minimum QSO failed.')
            return False
        if (a1.get_field('CALL').upper() == a2.get_field('CALL').upper()):
            if (a1.get_field('BAND').upper() == a2.get_field('BAND').upper()):
                if self.modeMatch(record1, record2):
                    if self.timeMatch(record1, record2):
                        match = True
        return match

    # -----------------------------------------------------------------------------
    def merge(self, from_record, into_record, update_fields=True):
        """
        Merge an ADIF record into another record.
        Adds missing fields from from_record into into_record.
        If update_fields is True, then existing fields in into_record are updated 
        with data in the corresponding field in from_record.
        
        Parameters
        ----------
        from_record : dict
            An ADIF QSO record passed as a Python dictionary.  This record is 
            merged into into_record.
        into_record : dict
            An ADIF QSO record passed as a Python dictionary. This record is
            modified to become the merged record.
        update_fields : bool
            If True, then existing fields in into_record can be modified by
            from_record if the information is different.  If False, then existing
            fields in into_record are not modified.
        
        Returns
        -------
        The following tuple is returned: (modified, merged_record)
        modified : bool
            True if into_record was modified, false otherwise.
        merged_record : dict
            The merged record as a Python dictionary.
            If the records don't match, then modified = False and an empty dictionary is returned.
        """
        modified = False
        merged_record = {}

        # Sanity checks.
        if not self.minimumQso(from_record): return (modified, merged_record)
        if not self.minimumQso(into_record): return (modified, merged_record)
        if not self.match(from_record, into_record): return (modified, merged_record)
    
        a_from = adif(from_record)
        a_into = adif(into_record)
    
        # Merge the QSO records.
        from_fields = a_from.get_field_names()
        for field in from_fields:
            data_from = a_from.get_field(field)
            if not a_into.has_field(field):
                # Add missing field.
                a_into.set_field(field, data_from)
                modified = True
                if self.Verbose:
                    self._print_msg("New field " + field + ": '" + data_from + "'")
            elif update_fields:
                data_into = a_into.get_field(field)
                if (data_from != data_into):
                    # Update field data.
                    a_into.set_field(field, data_from)
                    modified = True
                    if self.Verbose:
                        self._print_msg("Updated " + field + " from '" + data_into + "' to '" + data_from + "'")
    
        merged_record = a_into.get_record()
        return (modified, merged_record)

    # -----------------------------------------------------------------------------
    def minimumQso(self, record):
        """
        Determine if a QSO record has the minimum information needed to be a useful QSO.
        A minimal QSO record contains at least the CALL, BAND, MODE, QSO_DATE and TIME_ON fields.
    
        Parameters
        ----------
        record : dict
            An ADIF QSO record passed as a Python dictionary.
        
        Returns
        -------
        bool : True if minimum QSO criteria met, False otherwise.
        """
        ok = False
        a1 = adif(record)
        
        # Check for minimum QSO fields.
        if  (a1.has_field('CALL')) and (a1.has_field('BAND')) and (a1.has_field('MODE')) and \
            (a1.has_field('QSO_DATE')) and (a1.has_field('TIME_ON')):
                ok = True
        return ok

    # -----------------------------------------------------------------------------
    def modeMatch(self, record1, record2):
        """
        Determine if two QSO modes match.
        Compare modes and submodes as needed to determine if the modes are equivalent.
        
        Example: mode1 = PSK31; mode2 = PSK, submode2 = PSK31 -> modes match
        
        Parameters
        ----------
        record1 : dict
            An ADIF QSO record passed as a Python dictionary.
        record2 : dict
            An ADIF QSO record passed as a Python dictionary.
        
        Returns
        -------
        bool : True if modes match, False otherwise.
        """
        match = False
        a1 = adif(record1)
        a2 = adif(record2)
        
        m1 = a1.get_field('MODE').upper()
        m2 = a2.get_field('MODE').upper()
        
        sm1 = a1.get_field('SUBMODE').upper()
        sm2 = a2.get_field('SUBMODE').upper()
        
        has_sm1 = (len(sm1) > 0)  # Not all logs have submodes
        has_sm2 = (len(sm2) > 0)
        
        if ((len(m1) == 0) or (len(m2) == 0)): return False
        
        if (m1 == m2):
            if (has_sm1 and has_sm2):
                if (sm1 == sm2): match = True
            else:
                match = True            # Assume match if one or both submodes missing
        elif (m1 == sm2): match = True
        elif (m2 == sm1): match = True
        
        return match

    # -----------------------------------------------------------------------------
    def timeMatch(self, record1, record2):
        """
        Determine if the time difference between two records is close enough to be
        considered a match.
        The maximum time difference in seconds is contained in the MaxSeconds class 
        variable.
        Assumes the records have passed the minimumQso() check.
        
        Parameters
        ----------
        record1 : dict
            An ADIF QSO record passed as a Python dictionary.
        record2 : dict
            An ADIF QSO record passed as a Python dictionary.
        
        Returns
        -------
        bool : True if records match, False otherwise.
        """
        match = False
        a1 = adif(record1)
        a2 = adif(record2)
        td = timedelta()
    
        d1 = a1.get_field('QSO_DATE')
        d2 = a2.get_field('QSO_DATE')
        t1 = a1.get_field('TIME_ON')
        t2 = a2.get_field('TIME_ON')
    
        # Seconds are not always included in the TIME_ON field
        t1sec = 0
        t2sec = 0
        if (len(t1) > 4): t1sec = int(t1[4:6])
        if (len(t2) > 4): t2sec = int(t2[4:6])
    
        dt1 = datetime(int(d1[0:4]), int(d1[4:6]), int(d1[6:8]), int(t1[0:2]), int(t1[2:4]), t1sec)
        dt2 = datetime(int(d2[0:4]), int(d2[4:6]), int(d2[6:8]), int(t2[0:2]), int(t2[2:4]), t2sec)
        td  = abs(dt1 - dt2)
        if (td.days == 0) and (td.seconds <= self.MaxSeconds):
            match = True
        return match    


###############################################################################
# QSL received class.
###############################################################################
class qslrcvd(object):
    """
    A class for determining QSL received status from ADIF records.
    """
    
    # ------------------------------------------------------------------------
    def __init__(self):
        """
        Class constructor.
        """
        # Variable initialization.
        self.__version__ = str("0.1")  # Version per PEP 396
        
    # ------------------------------------------------------------------------
    def clublog_rcvd(self, qso):
        """
        Determine if a QSL was received via ClubLog.
        
        Parameters
        ----------
        qso : dict
            An ADIF QSO record passed as a Python dictionary.
        
        Returns
        -------
        bool : True if an affirmative ClubLog QSL record is found, 
            False otherwise.
        """
        qsl = False
        myAdif = adif(qso)
        clublog_qsl_rcvd = myAdif.get_field('APP_MASTERLOG_CLUBLOG_QSL')
        clublog_qslrdate = myAdif.get_field('APP_MASTERLOG_CLUBLOG_QSLRDATE')
        if (clublog_qsl_rcvd == 'Y') or (clublog_qsl_rcvd == 'V') or (len(clublog_qslrdate) > 0): qsl = True
        return qsl
        
    # ------------------------------------------------------------------------
    def eqsl_rcvd(self, qso):
        """
        Determine if a QSL was received via eQSL.cc.
        
        Parameters
        ----------
        qso : dict
            An ADIF QSO record passed as a Python dictionary.
        
        Returns
        -------
        bool : True if an affirmative eQSL.cc QSL record is found, 
            False otherwise.
        """
        qsl = False
        myAdif = adif(qso)
        eqsl_qsl_rcvd = myAdif.get_field('EQSL_QSL_RCVD')
        eqsl_qslrdate = myAdif.get_field('EQSL_QSLRDATE')
        if (eqsl_qsl_rcvd == 'Y') or (len(eqsl_qslrdate) > 0): qsl = True
        return qsl

    # ------------------------------------------------------------------------
    def lotw_qsl_rcvd(self, qso):
        """
        Determine if a QSL was received via ARRL Logbook of the World (LoTW).
        
        Parameters
        ----------
        qso : dict
            An ADIF QSO record passed as a Python dictionary.
        
        Returns
        -------
        bool : True if an affirmative LoTW QSL record is found, 
            False otherwise.
        """
        qsl = False
        myAdif = adif(qso)
        lotw_2xqsl = myAdif.get_field('APP_LOTW_2XQSL')
        lotw_qslmode = myAdif.get_field('APP_LOTW_QSLMODE')
        lotw_rxqsl = myAdif.get_field('APP_LOTW_RXQSL')
        lotw_qsl = myAdif.get_field('LOTW_QSL_RCVD')
        if (lotw_qsl == 'Y') \
            or (len(lotw_2xqsl) > 0) \
            or (len(lotw_qslmode) > 0) \
            or (len(lotw_rxqsl) > 0):
                qsl = True
        return qsl

    # ------------------------------------------------------------------------
    def qrz_qsl_rcvd(self, qso):
        """
        Determine if a QSL was received via QRZ.com.
        
        Parameters
        ----------
        qso : dict
            An ADIF QSO record passed as a Python dictionary.
        
        Returns
        -------
        bool : True if an affirmative QRZ.com QSL record is found, 
            False otherwise.
        """
        qsl = False
        myAdif = adif(qso)
        qrzlog_status = myAdif.get_field('APP_QRZLOG_STATUS')
        if (qrzlog_status == 'C'): qsl = True
        return qsl

   # ------------------------------------------------------------------------
    def qsl_rcvd(self, qso):
        """
        Determine if a QSL was received by any means.
        
        Parameters
        ----------
        qso : dict
            An ADIF QSO record passed as a Python dictionary.
        
        Returns
        -------
        bool : True if an affirmative QSL record is found, False otherwise.
        """
        myAdif = adif(qso)
        qsl_rcvd = myAdif.get_field('QSL_RCVD')
        if (qsl_rcvd == 'Y') or (qsl_rcvd == 'V'): return True
        
        clublog_qsl = self.clublog_rcvd(qso)
        if clublog_qsl: return True
        
        eqsl_qsl = self.eqsl_rcvd(qso)
        if eqsl_qsl: return True
        
        lotw_qsl = self.lotw_qsl_rcvd(qso)
        if lotw_qsl: return True
        
        qrz_qsl = self.qrz_qsl_rcvd(qso)
        if qrz_qsl: return True

        return False


###########################################################################
# Main program example test script.
# TODO: need to provide examples for adifMerge class.
# TODO: need to provide examples for qsl class.
########################################################################### 
if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Please specify an ADIF input file.")
        sys.exit(1)
        
    adif_file = sys.argv[1]
    
    count = 0
    myAdif = adif()
    adif_in = open(adif_file, 'r')
    while myAdif.next_record(adif_in):
        count += 1
        #print(myAdif.get_record() + '\n')  # Returns Python dictionary
        print(myAdif.get_adif() + '\n')     # Returns fully formatted ADIF record
    adif_in.close()

    if (len(myAdif.get_header()) > 0):
        print('Header fields:')
        print(myAdif.get_header())
    
    print(str(count) + ' ADIF records parsed.')
    sys.exit(0) 
    