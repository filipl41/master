import argparse
import glob
import os
import subprocess
import tempfile
import tkinter as tk

def compile_lto(source_files):
    tmp_folder = tempfile.mkdtemp()
    subprocess.run("clang {source_files} -O3 -o {exe_path} -flto -Wl,-plugin-opt=save-temps".format(source_files=source_files, exe_path=tmp_folder + "/exe"), shell=True)

    optimized_file = ""
    for filename in glob.glob(os.path.join(tmp_folder, '*.precodegen.*')):  
        optimized_file = filename
    result_ll = tmp_folder + "/result.ll"
    subprocess.run("llvm-dis {optimized_bc} -o {result_ll}".format(optimized_bc=optimized_file, result_ll=result_ll), shell=True)
    return result_ll
    
def compile_non_lto(source_files):
    tmp_folder = tempfile.mkdtemp()
    os.environ['LLVM_COMPILER'] = 'clang'
    exe_path = tmp_folder + "/exe"
    subprocess.run("wllvm -O3 {source_files} -o {exe_path}".format(source_files=source_files, exe_path=exe_path), shell=True)
    subprocess.run("extract-bc {exe_path}".format(exe_path=exe_path), shell=True)
    result_ll = tmp_folder + "/result.ll"
    subprocess.run("llvm-dis {exe_path} -o {result_path}".format(exe_path=exe_path + ".bc", result_path=result_ll), shell=True)
    return result_ll

def read_file(file):
    result = ""
    with open(file) as f:
        for line in f:
            result +=line
    return result

def show_files(string_lto, string_non_lto):
    root = tk.Tk()
    root.geometry("1200x700+200+150")
    non_lto_text = tk.Text(root, font=("times new roman",12))
    non_lto_text.insert(tk.END, string_lto)
    lto_text = tk.Text(root, font=("times new roman",12))
    lto_text.insert(tk.END, string_non_lto)

    non_lto_text.configure(state=tk.DISABLED)
    lto_text.configure(state=tk.DISABLED)
    lto_text.bind("<1>", lambda event: lto_text.focus_set())
    non_lto_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    non_lto_text.bind("<1>", lambda event: non_lto_text.focus_set())
    lto_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    tk.mainloop()

def compile_files(folder_path):
    source_files = ""
    for filename in glob.glob(os.path.join(folder_path, '*.cpp')):  
        source_files += filename + " "

    result_lto = compile_lto(source_files)
    result_non_lto = compile_non_lto(source_files)
    string_lto = read_file(result_lto)
    string_non_lto = read_file(result_non_lto)

    show_files(string_lto, string_non_lto)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="Input folder path", required=True)
    args = parser.parse_args()
    
    compile_files(args.input)



