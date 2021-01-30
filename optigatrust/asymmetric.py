# ============================================================================
# The MIT License
# 
# Copyright (c) 2018 Infineon Technologies AG
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE
# ============================================================================
from ctypes import *
import warnings
import hashlib

from optigatrust import core
from optigatrust.const import x, m1, m3, charge

__all__ = [
    'EccKey',
    'RsaKey',
    'EcdsaSignature',
    'RsaPkcs1v15Signature',
]


def _str2curve(curve_str, return_value=False):
    _map = {
        'secp256r1': m3.Curves.SEC_P256R1,
        'secp384r1': m3.Curves.SEC_P384R1,
        'secp521r1': m3.Curves.SEC_P521R1,
        'brainpoolp256r1': m3.Curves.BRAINPOOL_P256R1,
        'brainpoolp384r1': m3.Curves.BRAINPOOL_P384R1,
        'brainpoolp512r1': m3.Curves.BRAINPOOL_P512R1
    }
    if curve_str in _map:
        if return_value:
            return _map[curve_str].value
        else:
            return _map[curve_str]
    else:
        raise ValueError('Your curve ({0}) not supported use one of these: {1}'.format(curve_str, _map.keys()))


class _Signature:
    def __init__(self, hash_alg: str, key_id: int, signature: bytes, algorithm: str):
        self.hash_alg = hash_alg
        self.id = key_id
        self.signature = signature
        self.algorithm = algorithm


class EcdsaSignature(_Signature):
    def __init__(self, hash_alg, key_id, signature):
        signature_algorithm_id = '%s_%s' % (hash_alg, 'ecdsa')
        super().__init__(hash_alg, key_id, signature, signature_algorithm_id)


class RsaPkcs1v15Signature(_Signature):
    def __init__(self, hash_alg, keyid, signature):
        signature_algorithm_id = '%s_%s' % (hash_alg, 'rsa')
        super().__init__(hash_alg, keyid, signature, signature_algorithm_id)


class EccKey(core.Object):
    def __init__(self, key_id: int, curve='secp256r1'):
        super(EccKey, self).__init__(key_id)
        self._curve = curve
        self._pkey = None
        id_ref = self.optiga.key_id
        if key_id not in (id_ref.ECC_KEY_E0F0.value, id_ref.ECC_KEY_E0F1.value, id_ref.ECC_KEY_E0F2.value,
                          id_ref.ECC_KEY_E0F3.value) and key_id not in self.optiga.session_id_values:
            raise ValueError(
                'Your key_id {0} can\'t be sued to generate an ECC Key'.format(hex(key_id))
            )
        self._key_id = key_id
        self._key_usage = None
        self._hash_alg = None
        self._pkey = None
        self._signature = None

    @property
    def pkey(self):
        return self._pkey

    @property
    def curve(self):
        return self._curve

    @property
    def hash_alg(self):
        return self._hash_alg

    @property
    def key_id(self):
        return self._key_id

    @property
    def signature(self):
        return self._signature

    @property
    def key_usage(self):
        return self._key_usage

    def generate(self, curve='secp256r1', key_usage=None):
        """
        This function generates an ECC keypair, the private part is stored on the core based on the provided slot

        :param curve:
            Curve name, should be one of supported by the chip curves. For instance m3 has
            the widest range of supported algorithms: nistp256r1, nistp384r1, nistp521r1, bra

        :param key_usage:
            Key usage defined per string. Can be selected as following:
            ['key_agreement', 'authentication', 'encryption', 'signature']

        :raises:
            - TypeError - when any of the parameters are of the wrong type
            - OSError - when an error is returned by the core initialisation library

        :returns:
            EccKey object or None
        """
        _allowed_key_usage = {
            'key_agreement': self.optiga.key_usage.KEY_AGR,
            'authentication': self.optiga.key_usage.AUTH,
            'signature': self.optiga.key_usage.SIGN
        }
        _key_usage = list()
        if key_usage is None:
            _key_usage = [self.optiga.key_usage.KEY_AGR, self.optiga.key_usage.SIGN]
        else:
            for entry in key_usage:
                if entry not in _allowed_key_usage:
                    raise ValueError(
                        'Wrong Key Usage value {0}, supported are {1}'.format(entry, _allowed_key_usage.keys())
                    )
                _key_usage.append(_allowed_key_usage[entry])

        print(_key_usage)
        c = _str2curve(curve, return_value=True)
        if c not in self.optiga.curves_values:
            raise TypeError(
                "object_id not found. \n\r Supported = {0},\n\r  "
                "Provided = {1}".format(list(self.optiga.curves_values), c))

        self.optiga.api.exp_optiga_crypt_ecc_generate_keypair.argtypes = c_int, c_ubyte, c_bool, c_void_p, POINTER(
            c_ubyte), POINTER(
            c_ushort)
        self.optiga.api.exp_optiga_crypt_ecc_generate_keypair.restype = c_int

        c_keyusage = c_ubyte(sum(map(lambda ku: ku.value, _key_usage)))
        c_keyid = c_ushort(self.key_id)
        p = (c_ubyte * 150)()
        c_plen = c_ushort(len(p))

        ret = self.optiga.api.exp_optiga_crypt_ecc_generate_keypair(c, c_keyusage, 0, byref(c_keyid), p, byref(c_plen))

        pubkey = (c_ubyte * c_plen.value)()
        memmove(pubkey, p, c_plen.value)

        if ret == 0:
            self._pkey = bytes(pubkey)
            self._key_usage = _key_usage
            self._curve = curve
            return self
        else:
            raise IOError('Function can\'t be executed. Error {0}'.format(hex(ret)))

    def ecdsa_sign(self, data):
        """
        This function signs given data based on the provided EccKey object

        :param data:
            Data to sign, the data will be hashed based on the used curve.
            If secp256r1 then sha256, secp384r1 sha384 etc.

        :raises:
            - TypeError - when any of the parameters are of the wrong type
            - OSError - when an error is returned by the core initialisation library

        :returns:
            EcdsaSignature object or None
        """
        if not isinstance(data, bytes) and not isinstance(data, bytearray):
            if isinstance(data, str):
                _d = bytes(data.encode())
                warnings.warn("data will be converted to bytes type before signing")
            else:
                raise TypeError('Data to sign should be either bytes or str type, you gave {0}'.format(type(data)))
        else:
            _d = data

        self.optiga.api.exp_optiga_crypt_ecdsa_sign.argtypes = POINTER(c_ubyte), c_ubyte, c_ushort, POINTER(
            c_ubyte), POINTER(c_ubyte)
        self.optiga.api.exp_optiga_crypt_ecdsa_sign.restype = c_int
        _map = {
            'secp256r1': [hashlib.sha256, 32, 'sha256'],
            'secp384r1': [hashlib.sha384, 48, 'sha384'],
            'secp521r1': [hashlib.sha512, 64, 'sha512'],
            'brainpoolp256r1': [hashlib.sha256, 32, 'sha256'],
            'brainpoolp384r1': [hashlib.sha384, 48, 'sha384'],
            'brainpoolp512r1': [hashlib.sha512, 64, 'sha512']
        }
        # The curve should be one of supported, so no need for extra check
        param = _map[self.curve]
        # This lines are evaluates as following; i.e.
        # digest = (c_ubyte * 32)(*hashlib.sha256(_d).digest())
        # s = (c_ubyte * ((32*2 + 2) + 6))()
        # hash_algorithm = 'sha256'
        digest = (c_ubyte * param[1])(*param[0](_d).digest())
        # We reserve two extra bytes for nistp512r1 curve, shich has signature r/s values longer than a hash size
        s = (c_ubyte * ((param[1]*2 + 2) + 6))()
        hash_algorithm = param[2]

        c_slen = c_ubyte(len(s))
        self._hash_alg = hash_algorithm

        ret = self.optiga.api.exp_optiga_crypt_ecdsa_sign(digest, len(digest), self.key_id, s, byref(c_slen))

        if ret == 0:
            signature = (c_ubyte * (c_slen.value + 2))()
            signature[0] = 0x30
            signature[1] = c_slen.value
            memmove(addressof(signature) + 2, s, c_slen.value)

            return EcdsaSignature(hash_algorithm, self.key_id, bytes(signature))
        else:
            raise IOError('Function can\'t be executed. Error {0}'.format(hex(ret)))


class RsaKey(core.Object):
    def __init__(self, key_id: int):
        super(RsaKey, self).__init__(key_id)

        if key_id != 0xe0fc and key_id != 0xe0fd:
            raise ValueError(
                'key_id isn\'t supported should be either 0xe0fc, or 0xe0fd, you provided {0}'.format(hex(key_id))
            )
        self._key_usage = None
        self._key_size = None
        self._pkey = None

    @property
    def key_size(self):
        return self._key_size

    @property
    def pkey(self):
        return self._pkey

    @property
    def key_usage(self):
        return self._key_usage

    def generate(self, key_size=1024, key_usage=None):
        """
        This function generates an RSA keypair, the private part is stored on the core based on the provided slot

        :param key_size:
            Size of the key, can be 1024 or 2048

        :param key_usage:
            Key usage defined per string. Can be selected as following:
            ['key_agreement', 'authentication', 'encryption', 'signature']

        :param key_usage:
            A key usage indicator. The value should be the KeyUsage Enumeration. By default
            [KEY_AGR, AUTH, ENCRYPT]

        :raises:
            - TypeError - when any of the parameters are of the wrong type
            - OSError - when an error is returned by the core initialisation library

        :returns:
            RsaKey object or None
        """
        _allowed_key_usages = {
            'key_agreement': self.optiga.key_usage.KEY_AGR,
            'authentication': self.optiga.key_usage.AUTH,
            'encryption': self.optiga.key_usage.ENCRYPT,
            'signature': self.optiga.key_usage.SIGN
        }
        _key_usage = list()
        if key_usage is None:
            _key_usage = [self.optiga.key_usage.KEY_AGR, self.optiga.key_usage.SIGN]
        else:
            for entry in key_usage:
                if entry not in _allowed_key_usages:
                    raise ValueError(
                        'Wrong Key Usage value {0}, supported are {1}'.format(entry, _allowed_key_usages.keys())
                    )
                _key_usage.append(_allowed_key_usages[entry])

        _bytes = None
        api = self.optiga.api

        allowed_key_sizes = {1024, 2048}
        if key_size not in allowed_key_sizes:
            raise ValueError('This key size is not supported, you typed {0} (type {1}) supported are [1024, 2048]'.
                             format(key_size, type(key_size)))

        api.exp_optiga_crypt_rsa_generate_keypair.argtypes = c_int, c_ubyte, c_bool, c_void_p, POINTER(
            c_ubyte), POINTER(
            c_ushort)
        api.exp_optiga_crypt_rsa_generate_keypair.restype = c_int

        if key_size == 1024:
            c_keytype = 0x41
            rsa_header = b'\x30\x81\x9F\x30\x0D\x06\x09\x2A\x86\x48\x86\xF7\x0D\x01\x01\x01\x05\x00'
        else:
            c_keytype = 0x42
            rsa_header = b'\x30\x82\x01\x22\x30\x0d\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01\x05\x00'

        c_keyusage = c_ubyte(sum(map(lambda ku: ku.value, _key_usage)))
        c_keyid = c_ushort(self.id)
        p = (c_ubyte * 320)()
        c_plen = c_ushort(len(p))

        ret = api.exp_optiga_crypt_ecc_generate_keypair(c_keytype, c_keyusage, 0, byref(c_keyid), p, byref(c_plen))

        pubkey = (c_ubyte * c_plen.value)()
        memmove(pubkey, p, c_plen.value)

        if ret == 0:
            self._pkey = rsa_header + bytes(pubkey)
            self._key_usage = _key_usage
            self._key_size = key_size
            return self
        else:
            raise IOError('Function can\'t be executed. Error {0}'.format(hex(ret)))

    def pkcs1v15_sign(self, data: bytes or bytearray or str, hash_algorithm='sha256'):
        """
        This function signs given data based on the provided RsaKey object

        :param data:
            Data to sign

        :param hash_algorithm:
            Hash algorithm which should be used to sign data. SHA256 by default

        :raises:
            - TypeError - when any of the parameters are of the wrong type
            - OSError - when an error is returned by the core initialisation library

        :returns:
            RsaPkcs1v15Signature object or None
        """
        api = self.optiga.api

        if not isinstance(data, bytes) and not isinstance(data, bytearray):
            if isinstance(data, str):
                _d = bytes(data.encode())
                warnings.warn("data will be converted to bytes type before signing")
            else:
                raise TypeError('Data to sign should be either bytes or str type, you gave {0}'.format(type(data)))
        else:
            _d = data

        api.optiga_crypt_rsa_sign.argtypes = POINTER(c_ubyte), c_ubyte, c_ushort, POINTER(c_ubyte), POINTER(c_ubyte)
        api.optiga_crypt_rsa_sign.restype = c_int

        if hash_algorithm == 'sha256':
            digest = (c_ubyte * 32)(*hashlib.sha256(_d).digest())
            s = (c_ubyte * 320)()
            # Signature schemes RSA SSA PKCS1-v1.5 with SHA256 digest
            sign_scheme = 0x01
        elif hash_algorithm == 'sha384':
            digest = (c_ubyte * 48)(*hashlib.sha384(_d).digest())
            s = (c_ubyte * 320)()
            # Signature schemes RSA SSA PKCS1-v1.5 with SHA384 digest
            sign_scheme = 0x02
        else:
            raise ValueError('This key isze is not supported, you typed {0} supported are [\'sha256\', \'sha384\']'
                             .format(hash_algorithm))
        c_slen = c_uint(len(s))

        ret = api.exp_optiga_crypt_rsa_sign(sign_scheme, digest, len(digest), self.id, s, byref(c_slen), 0)

        if ret == 0:
            signature = (c_ubyte * c_slen.value)()
            memmove(addressof(signature), s, c_slen.value)
            print(bytes(signature))
            return RsaPkcs1v15Signature(hash_algorithm, self.id, bytes(signature))
        else:
            raise IOError('Function can\'t be executed. Error {0}'.format(hex(ret)))
