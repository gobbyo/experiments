from machine import Pin
import eightbyeight 
import time

class scrolldisplay:

    def __init__(self):
        #default/initialization
        self.rowpins = [26,18,9,20,2,8,3,6]
        self.colpins = [19,4,5,22,7,21,17,16]
        self.rpins = []
        self.cpins = []
        self.wait_time = 0.002

        for i in range(len(self.rowpins)):
            self.rpins.append(Pin(self.rowpins[i], Pin.OUT))
            self.rpins[i].low()
        
        for i in range(len(self.colpins)):
            self.cpins.append(Pin(self.colpins[i], Pin.OUT))
            self.cpins[i].low()
    
    def _createword(self,w):
        word = []
        for l in w:
            word.append(eightbyeight.matrix_in_binary(l))
        return word

    #Create a binary buffer for the entire word
    def _createtextbuffer(self, w, size):
        word = self._createword(w)
        buf = []
        row = 0
        while row < size:
            buf.append([])
            for letter in word:
                col = 0
                while col < size:
                    buf[row].append(letter[row][col])
                    col += 1
            row += 1
        return buf

    def _createframebuffer(self, size):
        buf = []
        i = 0
        for i in range(size):
            buf.append([0,0,0,0,0,0,0,0])
        return buf

    def _frame(self, buffer, offset, size):
        display = self._createframebuffer(size)
        col = 0
        while col < size:
            for row in range(size):
                buflen = len(buffer[row])
                if (row < size) and (col + offset < buflen):
                    display[row][col] = buffer[row][col + offset]
                else:
                    break
            col += 1
        return display

    def _paintscreen(self, buffer, scrollspeed):
        s = scrollspeed
        while s > 0:
            for colpin in self.cpins:
                colpin.high()
            row = 0
            for val in buffer:
                self.rpins[row].high()
                i = 0
                for colpin in self.cpins:
                    if val[i] > 0:
                        colpin.low()
                    i += 1
                time.sleep(self.wait_time)
                
                for colpin in self.cpins:
                    colpin.high()
                self.rpins[row].low()
                row += 1
            s -= 1

    def scroll(self, text, scrollspeed=5):
        buf = self._createtextbuffer(" {0}".format(text), 8)
        for i in range(len(buf[0])):
            f = self._frame(buf,i,8)
            self._paintscreen(f,scrollspeed)