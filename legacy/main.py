from Calculation import run_calculation
from DataHandler import CokidoDataHandler
from GsheetWrapper import GsheetWrapper
import time


# bug : update gsheet zegt dat het geen json is? ctiveer terug in calculate...

def main():
    doc = GsheetWrapper()
    sheet = doc.get_document()
    mydata = CokidoDataHandler(sheet)

    while True:
        val = mydata.get_runflag()
        if val == '1':
            print(time.ctime(), ' detected a 1 in cell D20, running calculation')
            mydata.set_runflag('Calculating')
            result = run_calculation()
            print('myresults:', result)
            mydata.set_runflag(result)
        else:
            print(time.ctime(), 'nothing detected')
        time.sleep(20)


if __name__ == '__main__':
    main()
