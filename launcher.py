import sys
import os
import subprocess
import time

# this file is a stripped down local version. 
#usually this stuff gets handled by my server backend file but thats not really usefull for personal use
#so i made this

#usage is | python launcher.py presentationurlhere |

# util
def splitString(strng, sep, pos):
    strng = strng.split(sep)
    return sep.join(strng[:pos]), sep.join(strng[pos:])

#main
def main():
   
    if len(sys.argv) < 2:
        print("Usage: python launcher.py <presentation_url>")
        sys.exit(1)

    link = sys.argv[1].strip()
    if not link:
        print("[!] Error: No link provided.")
        sys.exit(1)

    print(f"[*] Presentation URL: {link}")
    

    output_file = splitString(link, "/", -1)[1]  
    os.makedirs("pdfs", exist_ok=True)

    pdf_path = f"pdfs/{output_file}.pdf"

    #generate if not exist yet
    if os.path.exists(pdf_path):
        print(f"[+] PDF already exists at: {pdf_path}")
        print("[*] Exiting early.")
        sys.exit(0)

    print("[*] PDF not found locally. Launching bestConv.py...")
    
    try:
        subprocess.run(
            ["python", "bestConv.py", link],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"[!] Processing failed: {e}")
        sys.exit(1)

    # wait for PDF to be real
    print("[*] Waiting for disk write...")
    for _ in range(30):
        if os.path.exists(pdf_path):
            print("[+] pdf is now real")
            break
        print("no")
        time.sleep(1)

    # checking
    if not os.path.exists(pdf_path):
        print("[!] Error: PDF generation did not produce a file within 30 seconds.")
        sys.exit(1)
        
    print(f"[+] Success! File ready at: {os.path.abspath(pdf_path)}")

if __name__ == '__main__':
    main()