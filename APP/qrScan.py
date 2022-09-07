from fileinput import close
import webbrowser
import cv2
from pyzbar.pyzbar import decode
import base64
from algosdk.future.transaction import LogicSigAccount, PaymentTxn, LogicSigTransaction, wait_for_confirmation
from algosdk.v2client import algod
import ast
import json
from tkinter import *
from PIL import Image, ImageTk
import os
import sys



# Instantiate algod client
algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
algod_client = algod.AlgodClient(algod_token, algod_address)

# INPUT VARIABLES FOR BOOKSHOP
bookshop_address = "5ZHNQHTRBUI4ITTMZZBEUFP53EMSKNNNZ7ALSW2NTDMBOITSBRQI6JYV54"
student_class = "class1"
# Read from qr image and decode
# img = cv2.imread("./and_coreQR/cedolaQR.png")
# decoded = decode(img)
# print(decoded[0][0])


# Utility to destroy tkinter windows
def close(root):
    root.destroy()


# close window1 and open camera
def scanQR(root):
    close(root)
    openScanner()


# Save user input of amount for txn use, open window 3 (sending transaction)
def saveInput(root,addr,fee,lsig):
    global input 
    input = int(float(entry.get()) * 1000000) 
    global className 
    className = noteEntry.get()
    close(root) 
    window3(addr,fee,lsig)
    
# Utility to restart the qrScan program
def restart_program():
    os.execv(sys.executable, ['python'] + sys.argv)
    
    
def open_link(addr):
    webbrowser.open_new_tab("https://testnet.algoexplorer.io/address/" + addr)   
    
    
def openScanner():
        
    # Enable camera video capture
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(3, 640) # 3 == Width
    cap.set(4, 480) # 4 == Height
    camera = True
    qr_result = str()

    
    # Look for QR and decode it when found
    print("   >>>   Starting Qr Scanner....")
    while camera:
        success, frame = cap.read()
        for code in decode(frame):
            if code.data.decode('utf-8') != qr_result:
                qr_result = code.data.decode('utf-8')
                print(code.type)
                print(code.data.decode('utf-8'))
        
        
        # open camera frame    
        cv2.imshow("Testing-code-scan", frame)
        # scan every 1ms
        cv2.waitKey(1)
        
        # Exit program if camera window closed
        if not cv2.getWindowProperty('Testing-code-scan', cv2.WND_PROP_VISIBLE) < 1:
            # Break after successful QR scan and close camera
            if qr_result != "":
                print(" >>> QR code found <<<")
                cap.release()
                cv2.destroyAllWindows()
                break
        else:
            exit()
    
    # Save decoded result to file
    with open('and_coreQR/qrResult', "w") as f:
              f.write(qr_result)
              f.close()
    
    # Reopen
    with open('and_coreQR/qrResult', "r") as f:
        data = f.read()
        print(data)
            
    # Split data
    list = data.split(",")
    lsigb64 = list[0]
    addr = list[1]
    amount = list[2]
    fee = list[3]
    

    # UTF-8 Encode 
    encoded = lsigb64.encode() 
    print("\n\n encoded: {}".format(encoded))

    # b64 decode
    decoded = base64.urlsafe_b64decode(encoded).decode()
    print("\n\n Decoded Lsig: {}".format(decoded))

    # String to dictionary
    dic = ast.literal_eval(decoded)
    print("\n\n To Dictionary: {}".format(dic))

    # Decode encoded dictionary values
    dic["lsig"]["l"] = base64.urlsafe_b64decode(dic["lsig"]["l"])
    dic["lsig"]["sig"] = base64.urlsafe_b64decode(dic["lsig"]["sig"])
    dic["sigkey"] = base64.urlsafe_b64decode(dic["sigkey"])
    print("\n\n after decoding: {}".format(dic)) 

    # Build logic sig account object
    lsig = LogicSigAccount.undictify(dic)
    print(lsig) 

    print("\n\n   >>>   QR code decoded successfully")

    print("\n\n Preparing transaction from student account {} ".format(addr))

    account_info = algod_client.account_info(addr)
    bal = account_info.get("amount")
    
    # Build window 2 
    root = Tk()
    root.geometry("750x750")
    balance = Label(root,text="\n\n REMAINING ACCOUNT BALANCE: {} ALGO \n".format(bal / 1000000))
    hyperlink = Label(root,text= "Click to view transaction history", fg="blue",cursor="hand2")
    
    
    label = Label(root, text = "\n\nQR code decoded successfully \n Preparing transaction from student account {}".format(addr))
    label2 = Label(root, text="Transaction Amount: ")
    label3 = Label(root, text="Class Name: ")

    
    # Button to call saveInput function and continue with the transaction
    button2 = Button(root, text="Enter", command = lambda : saveInput(root,addr,fee,lsig))
    # Bind Return key to window/button2 for better user experience
    root.bind("<Return>", lambda event=None: button2.invoke())
    global entry
    entry = Entry(root, width=30)
    global noteEntry
    noteEntry = Entry(root,width=30)
    balance.pack()
    hyperlink.pack()
    hyperlink.bind("<Button-1>", lambda e: open_link(addr))
    label.pack()
    label2.pack()
    entry.pack()
    label3.pack()
    noteEntry.pack()
    button2.pack()
    root.mainloop()
    
def sendTransaction(addr,fee,lsig,root):
    
    # Labels for updating transaction progress (not working 100%)
    upd0 = Label(root, text="Sending Transaction.....")
    upd1 = Text(root,height=1)
    upd1.configure(bg=root.cget('bg'), relief="flat")
    upd2 = Label(root, text = "")
    upd3 = Label(root, text = "")
    upd4 = Label(root, text = "")
    upd5 = Label(root, text = "")
    err1 = Label(root, text = "")
    err2 = Label(root, text = "")
    upd0.pack()
    upd1.pack()
    upd2.pack()
    upd3.pack()
    upd4.pack()
    upd5.pack()
    err1.pack()
    err2.pack()
    
    if input == 0:
        upd2.config(text="Please restart and enter a valid amount")
        upd2.update()
        return
    elif not className:
        upd2.config(text="Please restart and enter a valid Class Name")
        upd2.update()
        return
    sender = addr
    receiver = bookshop_address # harcoded bookshop for test
    amount = int(input)
    fee = int(fee)
    note = "Class Name: {}".format(className)
    try:
        params = algod_client.suggested_params()
    except Exception:
        err1.config(text="Network connection failed. Please check that sandbox is connected to algod client")
        err1.update()
    params.fee = fee
    params.flat_fee = True
    closeTo = None
    lease = None
    rekeyTo = None
    print("\n\n >>> params.fee : {}".format(params.fee))
    
    txn = PaymentTxn(sender, params, receiver, amount, closeTo, note, lease, rekeyTo)
    print("\n\n transaction data")
    print(txn)

    LsigTxn = LogicSigTransaction(txn, lsig)
    print("\n\n Lsig transaction data")
    print(LsigTxn)

    account_info = algod_client.account_info(addr)
    bal = account_info.get("amount")
        
        
    try:
        txid = algod_client.send_transaction(LsigTxn)
        upd1.insert(1.0, "TXID: {}".format(txid))
        #upd1.config(text="TXID: {}".format(txid))
        upd1.update()
        print("TXID: ", txid)
        confirmed_txn = wait_for_confirmation(algod_client, txid, 4)  
        upd2.config(text="Result confirmed in round: {}".format(confirmed_txn['confirmed-round']))
        upd2.update()
        print("Result confirmed in round: {}".format(confirmed_txn['confirmed-round']))
        upd3.config(text="Transaction information: {}".format(json.dumps(confirmed_txn, indent=4)))
        upd3.update()
        print("Transaction information: {}".format(json.dumps(confirmed_txn, indent=4)))

        upd4.config(text="Transaction successfuly sent to bookshop OJW4R7C3SWQRO7KR4EI4H4KU7DVBW5EDDRMD63MGU2QJWHOVAHA6OGR2BU")
        upd4.update()
        
        
        account_info = algod_client.account_info(addr)
        bal = account_info.get("amount")
        upd5.config(text = "REMAINING ACCOUNT BALANCE: {} ALGO ".format(bal / 1000000))
        upd5.update()

        
        print("\n\n\n END<<< Lsig transaction successfully sent by (simulated) EmFi Wallet")
        print("        on behalf of student[0] to bookshop[0], without any additional signature\n\n\n")
    except Exception as err:
        try:
            e = str(err).split("invalid :", 1)[1]
            err1.config(text=e)
            err1.update()
            err2.config(text="Please double check the amount & receiver")
            err2.update()
        except Exception:
            
            #e = "account " + str(err).split(": account ", 1)[1]
            e = str(err).split("overspend", 1
                               )[0] + "overspend" + "\n" + "Tried to spend: " + str(err).split(
                                   "tried to spend",1)[1] + "\n" + "Account Balance: " + str(bal)
            err1.config(text=str(e))
            err1.update()
            err2.config(text="Please double check the account balance")
            err2.update()
            
                

        err1.config(text=e)
        err1.update()
        print(err)
        print("!!!!   Stopping ...")
        
        
    #restartButton.pack() ## NEEDS FIX - Restarts but the program doesn't end when you close windows after restarting
        


    
def window3(addr,fee,lsig):
    root= Tk()
    root.geometry("750x750")
    root.title("Sending Transaction")
    # restartButton = Button(root,text="Start Again", command=restart_program)
    root.after(5, sendTransaction(addr,fee,lsig,root))
    root.mainloop()

# Main code to open first window and create button to open QR Scanner
root = Tk()
root.geometry("600x384")
img = Image.open("./and_coreQR/emfiLogo.png")
resized = img.resize((600,384))
bg = ImageTk.PhotoImage(resized)
label1 = Label( root, image = bg)
label1.place(x = 0, y = 0)


# Open QR scanner
scanQrButton = Button(root, text="Scan Qr code", height=3, width=384, command = lambda : scanQR(root))
scanQrButton.pack(side=BOTTOM )
root.mainloop() 
exit()
    
