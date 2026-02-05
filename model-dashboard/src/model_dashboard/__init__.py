import os
import subprocess

def main() -> None:
    app_dir = os.path.dirname(os.path.abspath(__file__))
    subprocess.run('streamlit run app.py',shell=True,text=True,check=True,cwd=app_dir,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

