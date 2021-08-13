import argparse
import glob
import os
import subprocess
import tempfile
import tkinter as tk
import re


COLORS = ['alice blue', #'lavender', 'slate gray', 'blue',
    #'pale turquoise', 'turquoise',
    'cyan',  'dark green',  'lime green', 'yellow green',
    'indian red', 
    'dark salmon',  'orange', 
     'pink', 
    'violet red',
    'dark orchid',  'purple',
     'AntiqueWhite2',
    'PeachPuff3', 'PeachPuff4', 'NavajoWhite2', 'NavajoWhite3', 'NavajoWhite4',
    'cornsilk4', 
    'MistyRose4', 
    'SlateBlue4', 
    'PaleGreen3', 
    'gold2',
    'HotPink1', 
    'gray1']

color_index = 0

class ColorLineConnect:
    def __init__(self, llvm_line, color_index):
        self.llvm_lines = [llvm_line]
        self.color = COLORS[color_index]

class SourceFileConnect:
    def __init__(self, name) :
        self.source_file_name = name
        self.map = {}

    def insert(self, key, value):
        if key in self.map.keys():
            self.map[key].llvm_lines.append(value)
        else: 
            global color_index
            cl = ColorLineConnect(value, color_index)
            self.map[key] = cl
            color_index =  color_index + 1
            #color_index = color_index if color_index >= len(COLORS) else 0
        

def compile_lto(source_files):
    tmp_folder = tempfile.mkdtemp()
    subprocess.run("clang {source_files} -O3 -g -o {exe_path} -flto -Wl,-plugin-opt=save-temps".format(source_files=source_files, exe_path=tmp_folder + "/exe"), shell=True)

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
    subprocess.run("wllvm -O3 -g {source_files} -o  {exe_path}".format(source_files=source_files, exe_path=exe_path), shell=True)
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

def connect_source_llvm(llvm_ir_output):
    source_llvm_map = {}
    source_files = re.findall(".*DIFile.*\n", llvm_ir_output)
    for source_file in source_files:
        match = re.match("(\![0-9]+).*filename: (.*\.cpp).*", source_file)
        source_llvm_map[match.group(1)] = SourceFileConnect(match.group(2))
    for key in source_llvm_map.keys():
        matches = re.findall("(\![0-9]+).*file: {file}.*line: ([0-9]+).*".format(file=key), llvm_ir_output)
        for llvm_line, source_line  in matches:
            source_llvm_map[key].insert(source_line, llvm_line)

    for values in source_llvm_map.values():
        new_values = []
        for scope_values in values.map.values():
            for scope_value in  scope_values.llvm_lines:
                matches = re.findall("(\![0-9]+).*line: ([0-9]+).*scope: {scope}.*".format(scope=scope_value), llvm_ir_output)
                for llvm_line, source_line in matches:
                    new_values.append((source_line, llvm_line))
        for source_line, llvm_line in new_values:
            values.insert(source_line, llvm_line)        
       

    return source_llvm_map.values()

def parse_and_highlight(string_code, text_widget, connected_files):
    line_num = 1
    tag_num = 0
    string_list = string_code.splitlines()
    for code_line in string_list:
        for source_line in connected_files:
            for value_list in source_line.map.values():
                    for value in value_list.llvm_lines:
                        match = re.search(".*\!dbg {dbg_num}.*".format(dbg_num=value), code_line)
                        if match:
                            print(code_line)
                            debug = re.search(".*@llvm\.dbg\.value.*", code_line)
                            if debug:
                                continue
                            text_widget.tag_add("start{}".format(tag_num),"{line_num}.5 linestart".format(line_num=line_num), "{line_num}.5 lineend".format(line_num=line_num) )
                            text_widget.tag_config("start{}".format(tag_num), background= "{}".format(value_list.color), foreground= "black")
                            tag_num += 1

        line_num+=1


def insert_text(non_lto_text_widget, string_non_lto, lto_text_widget, string_lto, connected_files, string_source, string_text_widget):
    non_lto_text_widget.insert(tk.END, string_non_lto)
    lto_text_widget.insert(tk.END, string_lto)
    string_text_widget.insert(tk.END, string_source)
    connected_lto, connected_non_lto = connected_files
    #parse_and_highlight(string_lto, lto_text_widget, connected_lto)
    parse_and_highlight(string_non_lto, non_lto_text_widget, connected_non_lto)


def show_files(string_lto, string_non_lto, connected_files, source_files):
    root = tk.Tk()
    root.geometry("1200x700+200+150")
    non_lto_text = tk.Text(root, font=("times new roman",12))
    lto_text = tk.Text(root, font=("times new roman",12))
    source_file_text = tk.Text(root, font=("times new roman",12))
    print(source_files[0])
    insert_text(non_lto_text, string_non_lto, lto_text, string_lto, connected_files, read_file(source_files[0]), source_file_text)

    non_lto_text.configure(state=tk.DISABLED)
    lto_text.configure(state=tk.DISABLED)
    lto_text.bind("<1>", lambda event: lto_text.focus_set())
    non_lto_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    non_lto_text.bind("<1>", lambda event: non_lto_text.focus_set())
    lto_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    source_file_text.pack(fill=tk.BOTH, expand=True)
    source_file_text.configure(state=tk.DISABLED)
    tk.mainloop()

def compile_files(folder_path):
    source_files = ""
    for filename in glob.glob(os.path.join(folder_path, '*.cpp')):  
        source_files += filename + " "

    result_lto = compile_lto(source_files)
    result_non_lto = compile_non_lto(source_files)
    string_lto = read_file(result_lto)
    string_non_lto = read_file(result_non_lto)
    connected_files_non_lto = connect_source_llvm(string_non_lto)
    connected_files_lto = connect_source_llvm(string_lto)
    source_files_list = source_files.split()
    show_files(string_lto, string_non_lto, (connected_files_lto,connected_files_non_lto), source_files_list)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="Input folder path", required=True)
    args = parser.parse_args()
    
    compile_files(args.input)



