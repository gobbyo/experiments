#			C	o	l	u	m	n	s	
#		Pin	13	3	4	10	6	11	15	16
#		9	1	2	3	4	5	6	7	8
#	R	14	9	10	11	12	13	14	15	16
#	o	8	17	18	19	20	21	22	23	24
#	w	12	25	26	27	28	29	30	31	32
#	s	1	33	34	35	36	37	38	39	40
#		7	41	42	43	44	45	46	47	48
#		2	49	50	51	52	53	54	55	56
#		5	57	58	59	60	61	62	63	64

from machine import Pin
import time

rowpins =     [26,18,9,20,2,8,3,6]
colpins =     [19,4,5,22,7,21,17,16]

wait_time = 0.25

def main():
    
    rpin = []
    cpin = []

    for i in range(8):
        rpin.append(Pin(rowpins[i], Pin.OUT))
        rpin[i].low()
    
    for i in range(8):
        cpin.append(Pin(colpins[i], Pin.OUT))
        cpin[i].low()

    print("Press Ctrl-C to quit'")

    try:
        print("starting rows")
        
        for i in range(8):
            rpin[i].high()
            time.sleep(wait_time)
            rpin[i].low()

        time.sleep(wait_time)
        print("starting columns")

        for i in range(8):
            rpin[i].high()
        for i in range(8):
            cpin[i].high()

        for i in range(8):
            cpin[i].low()
            time.sleep(wait_time)
            cpin[i].high()

        print("count off")
        for i in range(8):
            rpin[i].low()

        row = 0
        for row in range(8):
            rpin[row].high()
            for col in range(8):
                cpin[col].low()
                time.sleep(wait_time/2)
                cpin[col].high()
            rpin[row].low()

    except KeyboardInterrupt:
        print("Program shut down by user")
    finally:
        print("Cleaning up and shutting down")

if __name__ == "__main__":
    main()