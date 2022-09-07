#
# Generates 1 account for every student in the Lista_Cedole csv file and The funding amount by class is imported from the
# Importi_Cedole csv file
# An account for a chosen number of bookshops is also generated

# Address, Private Key and Mnemonics for both students and bookshops are generated and stored in ./stud_data for future use
#
# Teal lsig contracts are generated for each student and stored in ./stud_contracts
#
# Minimum balance requirements are met by transferring an initial amount from a master account to each student and bookshop
# to ensure that each account is active, plus a smaller amount to cover to fees
#
# The transfer of the initial funding amount specified by the council in the CSV file is also transferred
# to each student respectively. This transfer is combined with the minimum balance transfer to save on transaction fees
#
# The teal contracts generated earlier are used to create Lsig objects, which are then encoded in a QR code
# The data encoded in the QR codes is stored in ./qr_data and the QR code images are stored in ./stud_QR
#
# TESTING:
# For testing purposes, the QR code IMAGE is read and decoded, and an Lsig object rebuilt.
# This is then compared to the original Lsig object (before it was encoded into the QR) to validate whether they are equal
#
# Finally, an Lsig transaction is sent from each student to one bookshop to test that transactions can be sent
# without the student's private key
# 
# Other tests passed in qrScan.py:
# Qr codes scanned successfully and valid lsig transactions sent successfully (valid amount and receiver)
# Overspend - transaction rejected
# Exceeding algo amount specified in teal contract - transaction rejected
# Invalid receiver - transaction rejected 
#
# Initial funding amount transferred per student verified to be accurate with the initial csv file amount
#
# Bookshop account imported to Pera Wallet using mnemonic and transaction sent to master account (REDEEMED) successfully



from algosdk import account, mnemonic, constants
from algosdk.future.transaction import LogicSigAccount, LogicSigTransaction, PaymentTxn, wait_for_confirmation
from algosdk.v2client import algod
import re
import base64
import json
import csv

import qrcode
import cv2
import ast
from pyzbar.pyzbar import decode

# SMART CONTRACTS PLACEHOLDERS as regexps
plhd_s_address = re.compile("!!ADDRESS!!")
plhd_receiver1 = re.compile("!!!RECEIVER1!!!")
plhd_receiver2 = re.compile("!!!RECEIVER2!!!")
plhd_amount = re.compile("!!!AMOUNT!!!")


# Instantiate algod client
algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
algod_client = algod.AlgodClient(algod_token, algod_address)

# Initial variables
num_bookshops = 2
max_amounts = ["1000000", "2000000", "3000000"] # arbitrary
master_account_address     = "CJRJE3UTTZ6JLZVFY4E33AQMOUJT44RTCMUYP7EU3S6ENJ2QS27QR6SXWA"
master_account_private_key = "ohEWBZ11hzC7BZL2oCqBv13CE3KooezkvnN6d03YEeMSYpJuk558lealxwm9ggx1Ez5yMxMph/yU3LxGp1CWvw=="

# STUDENTS number of students, addresses, private key, mnemonics, funding amounts(initial transfer)
stud_name = []
addr_stud = []
pk_stud = []
mn_stud = []
funding_amount = [] # amount of Emfi funding to transfer to student

# BOOKSHOPS number of bookshops, addresses, private key, mnemonics
addr_bookshop = []
pk_bookshop = []
mn_bookshop = []

# Lsig lists for testing
lsig_list = []
addr_list = []
addr_lsigs = {}


# Reads csv file containing a students name and the amount to transfer for that student
# Creates an account for each student and stores names, addresses, keys, mnemonics and funding amount in associated variables
def generate_student_accounts():

    # Get coupon based on class 
    with open("./tests/importi_cedole.csv", "r") as infile:
        reader = csv.reader(infile)
        next(reader)
        class_amounts = {row[1]:int((float(row[2]) * 1000000)) for row in reader}
        infile.close()
    
    
    with open("./tests/lista_cedole.csv", "r") as std_list:
        reader = csv.reader(std_list)
        for row in reader:
            # get id and class
            dic = {row[1]:row[2] for row in reader} 
            for id in dic:
                stud_name.append(id)
                if dic[id] in class_amounts:
                    funding_amount.append(str(class_amounts[dic[id]]))

        std_list.close()
        
    for i in range(len(dic)):
        private_key, address = account.generate_account()
        m = mnemonic.from_private_key(private_key)
        addr_stud.append(address)
        pk_stud.append(private_key)
        mn_stud.append(m)
    
    print("\n\n Generated {} student accounts".format(len(addr_stud)))
    
    stud_dict = dict(zip(addr_stud,pk_stud))    
    stud_tuple = tuple(zip(stud_name,addr_stud, pk_stud, mn_stud))
    return stud_dict,stud_tuple


# Generate bookshop accounts
def generate_bookshop_accounts():
    for i in range(num_bookshops):
        private_key, address = account.generate_account()
        m = mnemonic.from_private_key(private_key)
        addr_bookshop.append(address)
        pk_bookshop.append(private_key)
        mn_bookshop.append(m)
        
    book_tuple = tuple(zip(addr_bookshop,pk_bookshop,mn_bookshop))
    return book_tuple
        
        
# Create Lsig teal contracts    
def create_contract_code():
    for addr, amnt in zip(addr_stud, funding_amount): 
        with open("./tests/upd_teal.teal", "r") as inf:
            with open('./tests/stud_contracts/stud'+ addr +'.teal', 'w') as outf:
                for line in inf:
                    l1 = re.sub(plhd_s_address, addr, line, 0, 0)
                    l2 = re.sub(plhd_receiver1, addr_bookshop[0], l1,  0, 0)
                    l3 = re.sub(plhd_receiver2, addr_bookshop[1], l2, 0, 0)
                    l4 = re.sub(plhd_amount, amnt, l3, 0, 0)
                    outf.write(l4)


# Generate QR code for each student lsig
def create_student_qr(addr, lsig):
    print("Creating QR for student {} ...".format(addr))
    dict = lsig.dictify()
    print("\n\n  >> Dictified Lsig ")
    print(dict)
    
    # KL encode dictionary values to b64 (doesn't encode otherwise)
    
    dict["lsig"]['l'] = base64.urlsafe_b64encode(dict["lsig"]['l']).decode()
    dict["lsig"]['sig'] = base64.urlsafe_b64encode(dict["lsig"]['sig']).decode()
    dict["sigkey"] = base64.urlsafe_b64encode(dict["sigkey"]).decode()
    print("\n\n >>> Decoded bytes Dict: {}".format(dict))
    
    # KL b64 encode the dictionary 
    
    dictStr= json.dumps(dict)
    print("\n\n >>>> DictStr: {}".format(dictStr))
    encoded = dictStr.encode()
    print("\n\n >>>> DictBytes: {}".format(encoded))
    b64 = base64.urlsafe_b64encode(encoded)
    print("\n\n >>>> B64 Encoded DictStr: {}".format(b64))
    strEncoded = b64.decode()
    print("\n\n >>>> Final DATA: {}".format(strEncoded))
    
    # amount and fee are arbitrary but necessary for qr acceptance in kotlin app
    amount="1000000"
    fee="1000"
    address=addr
    encodedData = strEncoded
    comma = ","
    data = encodedData + comma + address + comma + amount + comma + fee
    print("\n\n >>> Data encoded into QR: {}".format(data))
    cedola = qrcode.make(data)    
    print(type(cedola))  # qrcode.image.pil.PilImage
    cedola.save("tests/stud_QR/qr" + addr + ".png")
    
    
    # KL save the data encoded in the QR to file for testing
    with open("tests/qr_data/data" + addr, "w") as f:
        f.write(data)
    
# Generate an lsig for each student, store lsig object for testing and call the QR generation function
def generate_lsigs(stud_dict):
    for addr in addr_stud:
    # Find and compile contract from teal generated files
        try:
            with open("./tests/stud_contracts/stud"+ addr + ".teal", "r") as contract_f:
                compiled_response = algod_client.compile(contract_f.read()) 
            print("Compiled result = ", compiled_response['result'])
            print("Compiled hash = ", compiled_response['hash'])
        except Exception as e:
            print("Error in teal compilation"+e)

        programstr = compiled_response['result']
        print("Complied program string : "+ programstr)

        t = programstr.encode()
        print("Encoded complied program string in bytes : ")
        print(t)

        program = base64.decodebytes(t)
        print("Decoded in base64 encoded compiled program string : ")
        print(program)

        lsig = LogicSigAccount(program)
        print("Generated lsig by the LogicSic(decoded program) :")
        print(lsig)

        lsig.sign(stud_dict[addr])
        
        # Append to lists for later testing
        lsig_list.append(lsig)
        addr_list.append(addr)
        
        
        create_student_qr(addr, lsig)
    return


# Sends minimum balance requirement. Includes an extra 10,000 to accommodate some transaction fees for future tests/transactions
def send_min_bal(addresses):
    params = algod_client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = constants.MIN_TXN_FEE 
    sender = master_account_address
    note = "Depositing minimum balance requirement".encode()
    amount = 110000 
    for i in range(len(addresses)):
        receiver = addresses[i]
        unsigned_txn = PaymentTxn(sender, params, receiver, amount, None, note)
        signed_txn = unsigned_txn.sign(master_account_private_key)   
            
        #submit transaction
        txid = algod_client.send_transaction(signed_txn)

        print("Successfully sent transaction with txID: {}".format(txid))

        # wait for confirmation 
        try:
            confirmed_txn = wait_for_confirmation(algod_client, txid, 4)  
        except Exception as err:
            print(err)
            print("!!!!   Stopping ...")
            return

        print("Transaction successfully accepted")

        # check accounts
        account_info = algod_client.account_info(master_account_address)
        print("Final MASTER account balance: {} microAlgos".format(account_info.get('amount')))

        account_info = algod_client.account_info(addresses[i])
        if addresses[0] == addr_stud[0]:
            print("Final STUDENT account for student: "+addr_stud[i])
            print("Account balance: {} microAlgos".format(account_info.get('amount')) + "\n")
            print(">>> END Send money from master to student {}      --------------------------------".format(addresses[i]))
        else:
            print("Final BOOKSHOP account for bookshop: "+addr_bookshop[i])
            print("Account balance: {} microAlgos".format(account_info.get('amount')) + "\n")
            print(">>> END Send money from master to bookshop {}      --------------------------------".format(addresses[i]))


# Send initial transfer of funding to students (amounts differing as per CSV file)
def initial_transfer():
    addr_amounts = dict(zip(addr_stud, funding_amount))
    params = algod_client.suggested_params()
    params.flat_fee = True
    params.fee = constants.MIN_TXN_FEE 
    sender = master_account_address
    note = "Initial funding transfer".encode()
    for addr in addr_stud:
        amount = int(addr_amounts[addr]) + 110000 # 110k for 100k min balance requirement and 10k allowance for fees
        receiver = addr
        unsigned_txn = PaymentTxn(sender, params, receiver, amount, None, note, None, None)
        signed_txn = unsigned_txn.sign(master_account_private_key)
        txid = algod_client.send_transaction(signed_txn)
        print("Successfully sent transaction with txID: {}".format(txid))

        # wait for confirmation 
        try:
            confirmed_txn = wait_for_confirmation(algod_client, txid, 4)  
        except Exception as err:
            print(err)
            print("!!!!   Stopping ...")
            return

        print("Transaction successfully accepted")

        # check accounts
        account_info = algod_client.account_info(master_account_address)
        print("Final MASTER account balance: {} microAlgos".format(account_info.get('amount')))

        account_info = algod_client.account_info(addr)
        print("Final STUDENT account balance: {} microAlgos".format(account_info.get('amount')))
    return

        
        
# Test that the post-qr code lsig object is equal to the lsig generated before encoding to the QR       
def test_lsig_rebuild(addr_lsigs):
    
    final_lsigs = []
    final_addr = []
    for addr in addr_stud:
        # Read and decode Qr code (from image)
        img = cv2.imread("./tests/stud_QR/qr" + addr + ".png")
        decoded = decode(img)
        data = decoded[0][0]
        data = data.decode()
        print("\n\n Lsig for student {} after reading from file: {}".format(addr,data))
        
        # Split data
        list = data.split(",")
        print("\n\n Data List: {}".format(list))
        lsigb64 = list[0]
        addr = list[1]
        amount = list[2] # Not needed
        fee = list[3] #  Not needed
        
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
        
        # Final Lsig
        finalLsig = LogicSigAccount.undictify(dic)
        
        # append to list for testing
        final_lsigs.append(finalLsig)
        final_addr.append(addr)
        
        print("\n\n Flsig OBJECT after decoding: {}".format(finalLsig))
        
        # Original Lsig 
        lsigBeforeQR = addr_lsigs[addr]

        print(">>>> Final LSIG >>>")
        print(finalLsig)
        print("\n")
        print("CHECKS on the loaded object: ... is it __eq__ to the original lsig object?")
        x = finalLsig.__eq__(lsigBeforeQR)
        print(x)
        print("\n\n\n")
        # a sanity check: if the two lsigs are not the same print their attributes one next to the other 
        if not x:
            print("The two lsig differ, here you have their logic, args, sig, msig")
            print("ATTENTION: we have had cases in which reading a QR code by an online services introduced an error - just one char changed!!!")      
            print(finalLsig.logic)
            print(lsigBeforeQR.logic)
            print(finalLsig.args)
            print( lsigBeforeQR.args)  
            print(finalLsig.sig)
            print( lsigBeforeQR.sig)
            print(finalLsig.msig)
            print(lsigBeforeQR.msig)
            return
    return dict(zip(final_addr, final_lsigs))   


# Send Lsig transactions to bookshop 0 from each student account, using the FINAL Lsig object (post qr)
def test_lsig_transactions(final_addr_lsigs):
    params = algod_client.suggested_params()
    params.flat_fee = True
    params.fee = constants.MIN_TXN_FEE 
    note = "Test lsig transaction".encode()
    amount = 1000
    receiver = addr_bookshop[0]
    
    for addr in addr_stud:
        txn = PaymentTxn(addr, params, receiver, amount, None, note, None, None)
        lsig_txn = LogicSigTransaction(txn, final_addr_lsigs[addr])
        txid = algod_client.send_transaction(lsig_txn)
        
        print("Successfully sent transaction with txID: {}".format(txid))

        # wait for confirmation 
        try:
            confirmed_txn = wait_for_confirmation(algod_client, txid, 4)  
        except Exception as err:
            print(err)
            print("!!!!   Stopping ...")
            return

        print("Transaction successfully accepted")
        
        # check accounts
        account_info = algod_client.account_info(addr)
        print("Final STUDENT account balance: {} microAlgos".format(account_info.get('amount')))
        
        # check accounts
        account_info = algod_client.account_info(addr_bookshop[0])
        print("Final BOOKSHOP account balance: {} microAlgos".format(account_info.get('amount')))
                
def main():
    print("\n\nEmFi core starting ...\n")

    account_info = algod_client.account_info(master_account_address)
    print("MASTER Account address "+master_account_address)
    print("MASTER Account private key "+master_account_private_key)
    print("MASTER Account balance:  microAlgos  {}".format(account_info.get('amount')) + "\n")
    print("Check that the master has sufficient tokens!")
    
        
    print("\n\n\n>>> algo client set up      --------------------------------")
    stud_dict, stud_tuple = generate_student_accounts()
    
    # Write student name, acc, pk and mn to file 
    with open("./and_core/stud_data/stud_acc_pk_mn.csv", "w") as f:
        outf = csv.writer(f)
        outf.writerow(["Stud_ID","Addr","Pvt_key", "Mnemonic"])
        for stud in stud_tuple:
            outf.writerow(stud)
        f.close()
    print("\n\nStudent account information written to file ./stud_data/stud_acc_pk_mn.csv")
    

    book_tuple = generate_bookshop_accounts()
    
    # Write bookshop acc, pk and mn to file
    with open("./and_core/stud_data/book_acc_pk_mn.csv", "w") as f:
        outf = csv.writer(f)
        outf.writerow(["Addr","Pvt_key", "Mnemonic"])
        for book in book_tuple:
            outf.writerow(book)
        f.close()
    print("\n\Bookshop account information written to file ./stud_data/book_acc_pk_mn.csv")
    print ("\n>>> end creation of accounts")
                
    print("\n\n\n>>> smart contracts set up      --------------------------------")
    create_contract_code()
    
    print("\n Contracts created and saved in ./stud_contracts")
    print(">>> end creation of smart contracts")
    # Make minimum balance requirement txns from master to students
    print("\n\n\n>>> Send minimum from master to students      --------------------------------")
   # send_min_bal(addr_stud)
    print("\n >>> END min balance transfers for students")
    print("\n\n\n>>> Send money from master to bookshops     --------------------------------")
    send_min_bal(addr_bookshop)
    print("\n >>> END min balance transfers for bookshops")
# #======================================================================  
    # Make initial transfers from master to studets
    print("\n\n        >>>>> Sending funding to students")
    initial_transfer()
    print("\n\n Funding transfers to students completed successfully")
    
    # Generate Lsigs and QR codes
    print("\n\n Begin generating Logic Signatures and QR codes for students")
    generate_lsigs(stud_dict)
    
    print("\n\n Lsigs and QRs successfully generated")
    
    # Dict for lsig comparison testing
    addr_lsigs = dict(zip(addr_list,lsig_list))
    
    # Test Lsig regeneration
    print("\n\n Beginning Testing.............")
    final_addr_lsigs = test_lsig_rebuild(addr_lsigs)
    
    print("\n\n >>>>>>> Testing of lsig rebuild complete")
    
    # Test Lsig transaction functionality
    print("\n\n Begin test lsig transactions..........")
    test_lsig_transactions(final_addr_lsigs)
    
    print("\n\n Lsig transactions sent successfully with final (rebuilt) logic signatures ")

main()