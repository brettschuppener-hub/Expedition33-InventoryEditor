import struct
import io
from typing import List

class FArchive:
    def __init__(self, data: bytes = b''):
        self.stream = io.BytesIO(data)
        self.size = len(data)

    def readBytes(self, n: int) -> bytes:
        b = self.stream.read(n)
        if len(b) < n:
            raise EOFError("Unexpected EOF")
        return b

    def writeBytes(self, b: bytes):
        self.stream.write(b)

    def readInt32(self) -> int:
        return struct.unpack('<i', self.readBytes(4))[0]

    def readUint32(self) -> int:
        return struct.unpack('<I', self.readBytes(4))[0]

    def writeInt32(self, val: int):
        self.stream.write(struct.pack('<i', val))

    def writeUint32(self, val: int):
        self.stream.write(struct.pack('<I', val))

    def readFString(self) -> bytes:
        length = self.readInt32()
        if length == 0:
            return b""
        if length > 0:
            return self.readBytes(length)
        else:
            return self.readBytes(-length * 2)

    def writeFString(self, b: bytes):
        if not b:
            self.writeInt32(0)
            return
        if len(b) > 0 and b[-1] == 0:
            self.writeInt32(len(b))
            self.stream.write(b)
        else:
            bNull = b + b'\x00'
            self.writeInt32(len(bNull))
            self.stream.write(bNull)

    def tell(self) -> int:
        return self.stream.tell()

    def seek(self, offset: int):
        self.stream.seek(offset)

    def getBuffer(self) -> bytes:
        return self.stream.getvalue()

    def atEnd(self) -> bool:
        return self.stream.tell() >= self.size

class UE5PropertyParser:
    """A higher level parser that can sequential read/write specific struct blocks."""
    def __init__(self, archive: FArchive):
        self.ar = archive





    def skipToProperty(self, propName: bytes) -> bool:
        """
        Safely jumps to the property using deterministic structural parsing.
        """
        self.ar.seek(0)
        if self.ar.readBytes(4) != b'GVAS': return False
        saveGameVersion = self.ar.readInt32()
        self.ar.readInt32()
        if saveGameVersion >= 3:
            self.ar.readInt32()
        self.ar.readBytes(10)
        self.ar.readFString()
        self.ar.readInt32()
        count = self.ar.readInt32()
        self.ar.readBytes(20 * count)
        self.ar.readFString()
        
        # Skip 1 byte padding before properties
        self.ar.readBytes(1)
        
        target = propName
        if not target.endswith(b"\x00"):
            target += b"\x00"
            
        while not self.ar.atEnd():
            name = self.ar.readFString()
            if name == b"None\x00" or not name:
                return False
                
            if name == target:
                return True
                
            typeName = self.ar.readFString()
            size1 = self.ar.readUint32()
            
            self.parseExtension(typeName)
            
            if typeName in (b"MapProperty\x00", b"ArrayProperty\x00", b"SetProperty\x00"):
                payloadSize = self.ar.readUint32()
                self.ar.seek(self.ar.tell() + payloadSize)
                self.ar.readBytes(1) # pad byte
            elif typeName == b"StructProperty\x00":
                if size1 == 1:
                    hasGuid = self.ar.readBytes(1)[0]
                    if hasGuid != 0:
                        self.ar.readBytes(16)
                    realSize = self.ar.readUint32()
                    self.ar.seek(self.ar.tell() + realSize)
                elif size1 == 2:
                    realSize = self.ar.readUint32()
                    self.ar.readBytes(1)
                    self.ar.seek(self.ar.tell() + realSize)
                else:
                    hasGuid = self.ar.readBytes(1)[0]
                    if hasGuid != 0:
                        self.ar.readBytes(16)
                    self.ar.seek(self.ar.tell() + size1)
            elif typeName in (b"NameProperty\x00", b"StrProperty\x00", b"IntProperty\x00", b"BoolProperty\x00", b"FloatProperty\x00", b"DoubleProperty\x00", b"EnumProperty\x00", b"UInt32Property\x00", b"UInt64Property\x00", b"ByteProperty\x00", b"TextProperty\x00"):
                if size1 == 0:
                    realSize = self.ar.readUint32()
                    self.ar.readBytes(1) # hasGuid
                    self.ar.seek(self.ar.tell() + realSize)
                else:
                    hasGuid = self.ar.readBytes(1)[0]
                    if hasGuid != 0:
                        self.ar.readBytes(16)
                    self.ar.seek(self.ar.tell() + size1)
            else:
                hasGuid = self.ar.readBytes(1)[0]
                if hasGuid != 0:
                    self.ar.readBytes(16)
                self.ar.seek(self.ar.tell() + size1)
            
        return False

    def skipStructPayload(self, target=None):
        while not self.ar.atEnd():
            name = self.ar.readFString()
            if name == b"None\x00" or not name:
                return False
            if target and name == target:
                return True
            typeName = self.ar.readFString()
            size1 = self.ar.readUint32()
            self.parseExtension(typeName)
            
            if name == b"LastUsedSavePoint\x00":
                actualSize = self.ar.readUint32()
                self.ar.readBytes(1) # Skip the 1-byte hasGuid/padding before payload
                self.ar.seek(self.ar.tell() + actualSize)
                continue
                
            if typeName in (b"MapProperty\x00", b"ArrayProperty\x00", b"SetProperty\x00"):
                payloadSize = self.ar.readUint32()
                self.ar.seek(self.ar.tell() + payloadSize)
                self.ar.readBytes(1)
            elif typeName == b"StructProperty\x00":
                if self.skipStructPayload(target):
                    return True
            elif typeName in (b"NameProperty\x00", b"StrProperty\x00", b"IntProperty\x00", b"BoolProperty\x00", b"FloatProperty\x00", b"DoubleProperty\x00", b"EnumProperty\x00", b"UInt32Property\x00", b"UInt64Property\x00", b"ByteProperty\x00", b"TextProperty\x00"):
                if size1 == 0:
                    realSize = self.ar.readUint32()
                    self.ar.readBytes(1) # hasGuid
                    self.ar.seek(self.ar.tell() + realSize)
                else:
                    hasGuid = self.ar.readBytes(1)[0]
                    if hasGuid != 0:
                        self.ar.readBytes(16)
                    self.ar.seek(self.ar.tell() + size1)
            else:
                hasGuid = self.ar.readBytes(1)[0]
                if hasGuid != 0:
                    self.ar.readBytes(16)
                self.ar.seek(self.ar.tell() + size1)
        return False

    def parseArrayHeader(self) -> dict:
        """Parses custom Array Property header metadata before elements."""
        typeName = self.ar.readFString() # ArrayProperty
        arrSize = self.ar.readUint32() # Array size field
        innerType = self.ar.readFString()
        if innerType == b"StructProperty\x00":
            pad1 = self.ar.readUint32()
            structName = self.ar.readFString()
            pad3 = self.ar.readUint32()
            structGuidPath = self.ar.readFString()
            pad5 = self.ar.readUint32()
            structGuidStr = self.ar.readFString()
            pad7 = self.ar.readUint32()
        else:
            pad1 = self.ar.readUint32()
        payloadSize = self.ar.readUint32()
        pad8 = self.ar.readBytes(1)
        elementCount = self.ar.readUint32()
        
        return {
            "typeName": typeName,
            "arrSize": arrSize,
            "innerType": innerType,
            "pad1": pad1,
            "structName": structName if 'structName' in locals() else None,
            "pad3": pad3 if 'pad3' in locals() else None,
            "structGuidPath": structGuidPath if 'structGuidPath' in locals() else None,
            "pad5": pad5 if 'pad5' in locals() else None,
            "structGuidStr": structGuidStr if 'structGuidStr' in locals() else None,
            "pad7": pad7 if 'pad7' in locals() else None,
            "payloadSize": payloadSize,
            "pad8": pad8,
            "elementCount": elementCount
        }

    def writeArrayHeader(self, hdr: dict):
        self.ar.writeFString(hdr["typeName"])
        self.ar.writeUint32(hdr["arrSize"])
        self.ar.writeFString(hdr["innerType"])
        self.ar.writeUint32(hdr["pad1"])
        if hdr["innerType"] == b"StructProperty\x00":
            self.ar.writeFString(hdr["structName"])
            self.ar.writeUint32(hdr["pad3"])
            self.ar.writeFString(hdr["structGuidPath"])
            self.ar.writeUint32(hdr["pad5"])
            self.ar.writeFString(hdr["structGuidStr"])
            self.ar.writeUint32(hdr["pad7"])
        self.ar.writeUint32(hdr["payloadSize"])
        self.ar.writeBytes(hdr["pad8"])
        self.ar.writeUint32(hdr["elementCount"])

    def readArrayPayload(self, propName: bytes) -> tuple:
        """Finds property, parses header, and returns (header, payloadBytes, originalData, headerStart, remainder)."""
        originalData = self.ar.getBuffer()
        
        self.ar.seek(0)
        if not self.skipToProperty(propName):
            return None
            
        headerStart = self.ar.tell()
        hdr = self.parseArrayHeader()
        payloadBytes = self.ar.readBytes(hdr["payloadSize"])
        remainder = self.ar.readBytes(self.ar.size - self.ar.tell())
        
        return hdr, payloadBytes, originalData, headerStart, remainder

    def rewriteArrayPayload(self, hdr: dict, newPayload: bytes, originalData: bytes, headerStart: int, remainder: bytes) -> bool:
        hdr["payloadSize"] = len(newPayload)
        out = FArchive()
        out.writeBytes(originalData[:headerStart])
        parserOut = UE5PropertyParser(out)
        parserOut.writeArrayHeader(hdr)
        out.writeBytes(newPayload)
        out.writeBytes(remainder)
        self.ar = out
        return True

    def isGuidString(self) -> bool:
        """Heuristic check for StructGuidStr FName which is missing for native structs."""
        pos = self.ar.tell()
        try:
            slen = self.ar.readInt32()
            if slen == 37:
                s = self.ar.readBytes(37)
                if s[-1] == 0 and s.count(b'-') == 4:
                    self.ar.readUint32() # Number
                    return True
            elif slen == 1:
                pass
        except:
            pass
        self.ar.seek(pos)
        return False

    def parseExtension(self, typeName: bytes):
        """Deterministically consumes the FPropertyTag extension based on type."""
        if typeName == b"StructProperty\x00":
            self.ar.readFString() # StructName
            self.ar.readUint32()  # Number
            self.ar.readFString() # StructPath
            self.ar.readUint32()  # Number
            self.isGuidString()
        elif typeName in (b"ArrayProperty\x00", b"SetProperty\x00"):
            inner = self.ar.readFString()
            self.ar.readUint32()
            self.parseExtension(inner)
        elif typeName == b"MapProperty\x00":
            keyType = self.ar.readFString()
            self.ar.readUint32()
            self.parseExtension(keyType)
            valType = self.ar.readFString()
            self.ar.readUint32()
            self.parseExtension(valType)
        elif typeName in (b"EnumProperty\x00", b"ByteProperty\x00"):
            self.ar.readFString()
            self.ar.readUint32()
            pos = self.ar.tell()
            has_path = False
            try:
                slen = self.ar.readInt32()
                if 0 < slen < 1000:
                    s = self.ar.readBytes(slen)
                    if s[-1] == 0 and (b'/' in s or s == b'None\x00'):
                        has_path = True
            except:
                pass
            self.ar.seek(pos)
            if has_path:
                self.ar.readFString()
                self.ar.readUint32()
        elif typeName == b"BoolProperty\x00":
            self.ar.readBytes(1) # Bool value is 1 byte inside the extension
        elif typeName == b"OptionalProperty\x00":
            valType = self.ar.readFString()
            self.ar.readUint32()
            self.parseExtension(valType)

    def parseMapHeader(self) -> dict:
        """Parses custom Map Property header metadata using robust extension parsing."""
        startPos = self.ar.tell()
        typeName = self.ar.readFString() # MapProperty
        unk1 = self.ar.readUint32()
        
        keyType = self.ar.readFString()
        self.ar.readUint32() # Number
        self.parseExtension(keyType)
        
        valType = self.ar.readFString()
        self.ar.readUint32() # Number
        self.parseExtension(valType)
        
        sizePos = self.ar.tell()
        payloadSize = self.ar.readUint32()
        unk4 = self.ar.readUint32()
        pad = self.ar.readBytes(1)
        count = self.ar.readUint32()
        
        endPos = self.ar.tell()
        self.ar.seek(startPos)
        rawHeader = self.ar.readBytes(endPos - startPos)
        
        return {
            "typeName": typeName,
            "keyType": keyType,
            "valType": valType,
            "payloadSize": payloadSize,
            "count": count,
            "rawHeader": rawHeader,
            "sizeOffset": sizePos - startPos
        }

    def writeMapHeader(self, hdr: dict):
        import struct
        # Update the payloadSize and count in the raw header
        raw = bytearray(hdr["rawHeader"])
        off = hdr["sizeOffset"]
        raw[off:off+4] = struct.pack('<I', hdr["payloadSize"])
        # count is the last 4 bytes of the header
        raw[-4:] = struct.pack('<I', hdr["count"])
        self.ar.writeBytes(bytes(raw))

    def readMapPayload(self, propName: bytes) -> tuple:
        originalData = self.ar.getBuffer()
        
        self.ar.seek(0)
        if not self.skipToProperty(propName):
            return None
            
        headerStart = self.ar.tell()
        hdr = self.parseMapHeader()
        
        elementsSize = hdr["payloadSize"] - 8
        payloadBytes = self.ar.readBytes(elementsSize)
        remainder = self.ar.readBytes(len(self.ar.getBuffer()) - self.ar.tell())
        
        return hdr, payloadBytes, originalData, headerStart, remainder

    def rewriteMapPayload(self, hdr: dict, newPayload: bytes, originalData: bytes, headerStart: int, remainder: bytes) -> bool:
        hdr["payloadSize"] = len(newPayload) + 8
        out = FArchive()
        out.writeBytes(originalData[:headerStart])
        parserOut = UE5PropertyParser(out)
        parserOut.writeMapHeader(hdr)
        out.writeBytes(newPayload)
        out.writeBytes(remainder)
        self.ar = out
        return True

    def parseEnumHeader(self) -> dict:
        typeName = self.ar.readFString() # EnumProperty
        size = self.ar.readUint32()
        unkIndex = self.ar.readUint32()
        enumType = self.ar.readFString()
        self.ar.readUint32() # Number
        
        pos = self.ar.tell()
        has_path = False
        try:
            slen = self.ar.readInt32()
            if 0 < slen < 1000:
                s = self.ar.readBytes(slen)
                if s[-1] == 0 and (b'/' in s or s == b'None\x00'):
                    has_path = True
        except:
            pass
        self.ar.seek(pos)
        enumPath = None
        if has_path:
            enumPath = self.ar.readFString()
            self.ar.readUint32()
            
        pad = self.ar.readBytes(1)
        return {
            "typeName": typeName, "size": size, "unkIndex": unkIndex,
            "enumType": enumType, "enumPath": enumPath, "pad": pad
        }

    def writeEnumHeader(self, hdr: dict):
        self.ar.writeFString(hdr["typeName"])
        self.ar.writeUint32(hdr["size"])
        self.ar.writeUint32(hdr["unkIndex"])
        self.ar.writeFString(hdr["enumType"])
        self.ar.writeUint32(0) # Number for enumType
        if hdr["enumPath"] is not None:
            self.ar.writeFString(hdr["enumPath"])
            self.ar.writeUint32(0)
        self.ar.writeBytes(hdr["pad"])

    def readEnumPayload(self, propName: bytes) -> tuple:
        originalData = self.ar.getBuffer()
        self.ar.seek(0)
        if not self.skipToProperty(propName):
            return None
        headerStart = self.ar.tell()
        hdr = self.parseEnumHeader()
        payloadBytes = self.ar.readBytes(hdr["size"])
        remainder = self.ar.readBytes(self.ar.size - self.ar.tell())
        return hdr, payloadBytes, originalData, headerStart, remainder

    def rewriteEnumPayload(self, hdr: dict, newPayload: bytes, originalData: bytes, headerStart: int, remainder: bytes) -> bool:
        hdr["size"] = len(newPayload)
        out = FArchive()
        out.writeBytes(originalData[:headerStart])
        parserOut = UE5PropertyParser(out)
        parserOut.writeEnumHeader(hdr)
        out.writeBytes(newPayload)
        out.writeBytes(remainder)
        self.ar = out
        return True
