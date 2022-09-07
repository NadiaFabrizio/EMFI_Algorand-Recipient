from numpy import int64
import pandas as pd
from algosdk.v2client import indexer, algod
import csv
import time
from tkinter import *
from tkinter import filedialog
from tkcalendar import *
from PIL import Image, ImageTk

# Council wallet to exclude from transactions
council = "J57QVZPP67ANQI6YSQXMBV5S5N6ZWNB2C2SWMKOTAEQGLOAIDSI6242XLA"

# Bookshop accounts to retrieve transactions from
bookshop1 = "CDEMSJXTS74WLRWKT6BCQNKH2K2JGPDSTJY2JVV35PV3ZSUKUVODF4H5B4"
bookshop2 = "VP43LXVBJXDEFT3VMY2QX3P54A2JQJ4FQJLGWOIVLMF6LYMKSUDIGM2NEY"

# Dates to retrieve transactions between
txn_start = "2022-05-26"
txn_end = "2022-05-27"
purestake_token = "JyTN4lTWi32T5bAO33vBT70UAlHMjlhVaXD0FJpM"

# API setup
algod_address = "https://testnet-algorand.api.purestake.io/ps2"
headers = {"X-Api-key": purestake_token}
algod_client = algod.AlgodClient(purestake_token, algod_address, headers)

headers = {
    "X-API-Key": purestake_token,
}

# Instantiate indexer
myindexer = indexer.IndexerClient(
    indexer_token= "",
    indexer_address="https://testnet-algorand.api.purestake.io/idx2",
    headers=headers
)


# Obtain all txns in a time period, given an address
def get_txns(addr, start, end):
    
    response = myindexer.search_transactions_by_address(
        address = addr, 
        start_time= start,
        end_time=end
    ) 
    
    transactions = response["transactions"]
    txn_df = pd.DataFrame(transactions)
    return txn_df


def prepare_txn(txn_df):
    
    # Filter for payments
    txn_filtered = txn_df[txn_df["tx-type"] == "pay"]
    
    # Retrieve useful columns
    txn_df_reduced = txn_filtered[["payment-transaction", "sender", "id","round-time"]]
    
    # Get amount (microAlgos) and receiver info from transaction
    txn_df_reduced["amount"] = txn_df_reduced["payment-transaction"].apply(pd.Series)["amount"]
    txn_df_reduced["receiver"] = txn_df_reduced["payment-transaction"].apply(pd.Series)["receiver"]
    txn_df_reduced.drop(["payment-transaction"], axis=1, inplace=True)
    
    # Format round-time to show the date
    txn_df_reduced["date"] = txn_df_reduced["round-time"].map(lambda x: time.ctime(x))
    txn_df_reduced.drop(["round-time"],axis=1, inplace=True)
 
    
    return txn_df_reduced



# Ignore txns from council to bookshops
def exclude_council_txns(txn):
    
    no_noise = txn [(txn.sender != council)]    
    return no_noise


    
def generate_files(folder_path, cal, cal1):

    # Get dates from calendar variables
    from_date = cal.get_date()
    to_date = cal1.get_date()
    
    # Reformat date for API call
    def format_date(in_date):
        s1 = in_date.split("/")
        s2 = int(s1[2]) + 2000
        if len(s1[0]) == 1:
            s3 = "0" + s1[0]
        else:
            s3 = s1[0]
        s4 = s1[1]
        out_date = str(s2) + "-" + s3 + "-" + s4
        return out_date
    
    start = format_date(from_date)
    end = format_date(to_date)
    
    # Get initial transactions
    txn_df = get_txns(bookshop1,start, end)
    txn_df2 = get_txns(bookshop2,start, end)
        
    # Clean df and retrieve useful info
    txn_cleaned = prepare_txn(txn_df)
    txn_cleaned2 = prepare_txn(txn_df2)

    txn_grouped = exclude_council_txns(txn_cleaned)
    txn_grouped2 = exclude_council_txns(txn_cleaned2)

    print(txn_grouped)

    # Write individual bookshop transactions to files
    # txn_grouped.to_csv(path_or_buf= folder_path.get() + "/" + bookshop1 + "_txns.csv", index=False)
    # txn_grouped2.to_csv(path_or_buf= folder_path.get() + "/" + bookshop2 + "_txns.csv", index=False)

    # Concatenate bookshop transactions to one DF
    all_txns = [txn_grouped2,txn_grouped]
    all_txns = pd.concat(all_txns)

    # Read stud_id / account data for cross-referencing
    # This path & file needs to be set in the council's system
    #   either manually hard-coded or by selecting the file in the interface
    with open("./and_core/stud_data/stud_acc_pk_mn.csv", "r") as stud_data:
        reader = csv.reader(stud_data)
        # Create dictionary of id : addr
        for row in reader:
            id_addr = {row[0]:row[1] for row in reader}
            
    # Create DF to enable merging of Dataframes by Address, using ID
    columns = ["ID_MINORE", "sender"]
    c2 = [id_addr.keys(),id_addr.values()]
    new_dict = dict(zip(columns, c2))
    id_df = pd.DataFrame.from_dict(new_dict)

    # Merge DFs
    # Need to do this to add transaction data to Lista_cedole file accurately
    merged = pd.merge(id_df,all_txns)

    print(merged)

    # Create DF from lista_cedole
    # This path also needs to be set by council as input or hard-coded
    with open("./tests/lista_cedole.csv", "r") as f:
        cedole = pd.read_csv(f)
        
    print(cedole)

    # Change type to enable merging
    merged["ID_MINORE"] = merged["ID_MINORE"].astype(int64)
    

    # Merge by ID
    new_merged = pd.merge(merged,cedole)

    print(new_merged)

    # Clean up DF and rename columns to correct format
    new_merged.drop(["DATA_TRANSAZIONE"],axis=1, inplace=True)
    new_merged.drop(["IMPORTO_TRANSAZIONE"],axis=1, inplace=True)
    new_merged.drop(["NUMERO_TRANSAZIONE"],axis=1, inplace=True)
    new_merged.drop(["sender"],axis=1, inplace=True)
    new_merged.rename(
        columns={"id":"NUMERO_TRANSAZIONE", "date": "DATA_TRANSAZIONE", "amount":"IMPORTO_TRANSAZIONE"}, inplace=True)

    # Rearrange columns in the correct order
    cols = ['ANNO_SCOLASTICO','ID_MINORE','CLASSE','CODICE_SCUOLA','NUMERO_TRANSAZIONE','DATA_TRANSAZIONE','IMPORTO_TRANSAZIONE']
    outfile = new_merged[cols]

    # Write DF to csv file
    outfile.to_csv(path_or_buf= folder_path.get() + "/final_lista_cedole.csv", index=False)

    # Sort values for Riepologo Contabile file
    for_sorting = ["ANNO_SCOLASTICO","receiver","CODICE_SCUOLA","CLASSE","IMPORTO_TRANSAZIONE","NUMERO_TRANSAZIONE"]

    new_merged = new_merged[for_sorting]
    new_merged.sort_values("receiver")
    new_merged.sort_values("CODICE_SCUOLA")
    new_merged.sort_values("CLASSE")

    new_merged.rename(columns={"receiver":"CODICE_LIBRAIO"}, inplace=True)

    print(new_merged)

    # Write DF to CSV riepologo_contabile
    new_merged.to_csv( folder_path.get() + "/riepologo_contabile.csv", index=False)

    
# Enable browser for choosing the path to save the files
def browse_button():
    # Allow user to select a directory and store it in global var called folder_path
    filename = filedialog.askdirectory()
    folder_path.set(filename)
    
        
def main():
    # Main code to open first window
    root = Tk()
    root.geometry("600x384")
    img = Image.open("./and_coreQR/emfiLogo.png")
    resized = img.resize((600,384))
    bg = ImageTk.PhotoImage(resized)
    label1 = Label( root, image = bg)
    label1.place(x = 0, y = 0)
    
    # Frames for calendars
    f1 = Frame(root,height=150,width=200)
    f1.pack_propagate(0)
    f2 = Frame(root,height=150,width=200)
    f2.pack_propagate(0)
    
    # Add Calendars
    f1.place(anchor=W,rely=0.3,relx=0.15)
    cal = Calendar(f1, selectmode = 'day',
               year = 2020, month = 5,
               day = 22)
    cal.pack()
    f2.place(anchor=E, relx = 0.9, rely=0.3)
    cal1 = Calendar(f2, selectmode = 'day',
               year = 2020, month = 5,
               day = 22)
    cal1.pack()
    
    # Scratch variable for saving the chosen path
    global folder_path
    folder_path = StringVar()
    
    lbl1 = Label(
        root,text="Please choose the dates to see transactions from, and a location to save the generated files", height=2)
    lbl1.place(anchor=CENTER,relx=0.5,rely=0.05)
    
    lbl2 = Label(master=root,textvariable=folder_path)
    lbl2.place(anchor=W, relx=0.05,rely=0.6)
   
    button2 = Button(text="Browse", height=2, width=20,command=browse_button)
    button2.place(anchor=CENTER, relx=0.5,rely=0.7)
    
    generateFilesButton = Button(root, text="Generate Reports", height=3, width=384, command = lambda: generate_files(folder_path, cal, cal1))
    generateFilesButton.pack(side=BOTTOM)
    
    root.mainloop() 
    

    
main()