# coding=utf-8
import re
import math


# Tools
class Utility:
    # Serialization
    @staticmethod
    def serialize_instance(obj):
        d = {'__classname__': obj.__class__.__name__ }
        d.update(vars(obj))
        return d

    # Deserialization
    @staticmethod
    def unserialize_object(d, classes={}):
        clsname = d.pop('__classname__', None)
        if clsname:
            cls = classes[clsname]
            obj = cls()  # Make instance without calling __init__
            for key, value in d.items():
                setattr(obj, key, value)
            return obj
        else:
            return d

    # Formatting time string
    @staticmethod
    def getTimeStr(ts):
        import time
        t = time.gmtime(ts)
        timeStr = time.strftime('%Y-%m-%dT%H:%M:%SZ', t)
        return timeStr

    @staticmethod
    def ieee754Int2Float(a, p):
        f = ((-1) ** ((a & 0x80000000) >> 31)) * (2 ** (((abs(a) & 0x7f800000) >> 23) - 127)) * (1+((abs(a) & 0x7fffff)*1.0/(2**23)))
        return round(f, p)

    # Ieee754 conversion
    @staticmethod
    def Float2ieee754Words(f, byte_order):
        if f == 0:
            return [0, 0]

        words = []

        signedBit = 0 if f > 0 else 1

        stepBits = int(math.floor(math.log(abs(f), 2)))
        tailBits = int(((abs(f) / (2 ** stepBits)) - 1) * (2 ** 23)) if stepBits > 0 else int(
            (abs(f) / (2 ** stepBits)) * (2 ** 23))  # int(((f/(2**stepBits))-1) * (2**23))

        dw = ((signedBit << 31) & 0x80000000) | (((stepBits + 127) << 23) & 0x7f800000) | (tailBits & 0x7fffff)
        wh = (dw & 0xffff0000) >> 16
        wl = dw & 0xffff
        if re.search(r'(^cdab$)', byte_order) is not None:
            words.append(wl)
            words.append(wh)
        elif re.search(r'(^abcd$)', byte_order) is not None:
            words.append(wh)
            words.append(wl)
        elif re.search(r'(^badc$)', byte_order) is not None:
            words.append(((wh & 0xff) << 8) | ((wh & 0xff00) >> 8))
            words.append(((wl & 0xff) << 8) | ((wl & 0xff00) >> 8))
        else:  # r'(^dcba$)'
            words.append(((wl & 0xff) << 8) | ((wl & 0xff00) >> 8))
            words.append(((wh & 0xff) << 8) | ((wh & 0xff00) >> 8))
        return words

    @staticmethod
    def ieee754Words2Float(wl, wh, p):
        a = wh << 16 | wl
        # f = ((-1) ** ((a & 0x80000000) >> 31)) * (2 ** (((a & 0x7f800000) >> 23) - 127)) * (1 + ((a & 0x7fffff) / (2 ** 23 * 1.0)))
        # f = ((-1) ** ((a & 0x80000000) >> 31)) * (2 ** (((a & 0x7f800000) >> 23) - 127)) * (1 + (math.log((a & 0x7fffff), 2)))
        return Utility.ieee754Int2Float(a, p)

    # int -> words[2]
    @staticmethod
    def toWords(d, byte_order):
        wh = (abs(d) & 0xffff0000) >> 16
        wl = abs(d) & 0xffff
        words = []
        if d < 0:
            wh = wh | 0x8000
        if re.search(r'(^cdab$)', byte_order) is not None:
            words.append(wl)
            words.append(wh)
        elif re.search(r'(^abcd$)', byte_order) is not None:
            words.append(wh)
            words.append(wl)
        elif re.search(r'(^badc$)', byte_order) is not None:
            words.append(((wh & 0xff) << 8) | ((wh & 0xff00) >> 8))
            words.append(((wl & 0xff) << 8) | ((wl & 0xff00) >> 8))
        else:  # r'(^dcba$)'
            words.append(((wl & 0xff) << 8) | ((wl & 0xff00) >> 8))
            words.append(((wh & 0xff) << 8) | ((wh & 0xff00) >> 8))
        return words

    # bytes[2] -> word
    @staticmethod
    def toWord(l, h, byte_order, vtype):
        if re.search(r'(^ba($|dc$))|(^dcba$)', byte_order) is not None:
            if re.search('^unsigned ', vtype):
                t = (((l & 0x7f) << 8) & (((l & 0x8) << 8) & 0xff00) | h)
                return t
            else:
                t = ((l << 8) & 0xff00) | h
                return t
        else:
            if re.search('^unsigned ', vtype):
                t = (((h & 0x7f) << 8) & (((h & 0x8) << 8) & 0xff00) | l)
                return t
            else:
                t = ((h << 8) & 0xff00) | l
                return t

    # words[2] -> double words (int)
    @staticmethod
    def toDWord(l0, h0, l1, h1, byte_order, vtype):
        if re.search(r'^dcba$', byte_order) is not None:
            if re.search('^unsigned ', vtype):
                t = ((l1 & 0xff) << 24) | (h1 << 16) | (l0 << 8) | h0
            else:
                s = (((l1 & 0x7f) << 24) & 0xff000000) | ((h1 << 16) & 0xff0000) | ((l0 << 8) & 0xff00) | (h0 & 0xff)
                t = s if (l1 & 0x80) == 0 else (0 - s)

        elif re.search(r'^cdab$', byte_order) is not None:
            if re.search('^unsigned', vtype):
                t = ((h1 & 0xff) << 24) | (l1 << 16) | (h0 << 8) | l0
            else:
                s = (((h1 & 0x7f) << 24) & 0xff000000) | ((l1 << 16) & 0xff0000) | ((h0 << 8) & 0xff00) | (l0 & 0xff)
                t = s if (h1 & 0x80) == 0 else (0 - s)

        elif re.search(r'^badc$', byte_order) is not None:
            if re.search('^unsigned', vtype):
                t = ((l0 & 0xff) << 24) | (h0 << 16) | (l1 << 8) | h1
            else:
                s = (((l0 & 0x7f) << 24) & 0xff000000) | ((h0 << 16) & 0xff0000) | ((l1 << 8) & 0xff00) | (h1 & 0xff)
                t = s if (l0 & 0x80) == 0 else (0 - s)

        else:
            if re.search('^unsigned', vtype):
                t = ((h0 & 0xff) << 24) | (l0 << 16) | (h1 << 8) | l1
            else:
                s = (((h0 & 0x7f) << 24) & 0xff000000) | ((l0 << 16) & 0xff0000) | ((h1 << 8) & 0xff00) | (l1 & 0xff)
                t = s if (h0 & 0x80) == 0 else (0 - s)
        return t

    # ieee754 , byte[4] -> float
    @staticmethod
    def toFloat(l0, h0, l1, h1, byte_order, vtype):
        t = Utility.toDWord(l0, h0, l1, h1, byte_order, vtype)
        return Utility.ieee754Int2Float(t, 2)  # ieee754 converting, precision: default 2

    # [1, 2, 3] -> [[1, 2], [3, 0]]
    @staticmethod
    def toDoubleList(v):
        lenght = len(v)
        if (lenght % 2) == 0:
            return [[v[i], v[i + 1]] for i in xrange(0, lenght, 2)]
        else:
            return [[v[i], 0 if lenght - 1 == i else v[i + 1]] for i in xrange(0, lenght + 1, 2)]


if __name__ == '__main__':
    v=float("2.2")
    print(str(v))
    (wl, wh)=Utility.Float2ieee754Words(v, "abcd")
    dw =((wh & 0xffff) << 16) | (wl & 0xffff)
    bhh=(wh&0xff00)>>8
    bhl=wh&0x00ff
    blh=(wl & 0xff00)>>8
    bll=wl & 0xff
    print(""+str(bhh)+"-"+str(bhl)+"-"+str(blh)+"-"+str(bll))
    f = Utility.ieee754Int2Float(dw, 2)
    print(f)
    s = Utility.ieee754Int2Float(0x42c88000, 3)
    print(s)