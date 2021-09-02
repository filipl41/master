import argparse
import glob
import os
import subprocess
import tempfile
import tkinter as tk
import re
import difflib
from datetime import datetime, timezone

COLORS = ['alice blue', 'lavender', 'slate gray',
    'pale turquoise', 'turquoise',
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

class ColorLineConnect:
    def __init__(self):
        self.color_index = 0
        self.map = {}

    def insert(self, source_line):
        if source_line not in self.map.keys():
            self.map[source_line] = COLORS[self.color_index]
            self.color_index +=1
            self.color_index = self.color_index if self.color_index < len(COLORS) else 0

color_line_map = ColorLineConnect()
llvm_debug_line_map = {}
next_source_file_index = 0
encoded_real_instruction_map = {}

class SourceFileConnect:
    def __init__(self, name) :
        self.source_file_name = name
        self.map = {}

    def insert(self, key, value):
        if key in self.map.keys():
            self.map[key].append(value)
        else: 
            self.map[key] = [value]
            #color_index = color_index if color_index >= len(COLORS) else 0

def file_mtime(path):
    t = datetime.fromtimestamp(os.stat(path).st_mtime,
                               timezone.utc)
    return t.astimezone().isoformat()        

def compile_lto(source_files, optimization_level):
    tmp_folder = tempfile.mkdtemp()
    subprocess.check_output("clang++ {source_files} -O{level} -g -o {exe_path} -flto -Wl,-plugin-opt=save-temps".format(level=optimization_level, source_files=source_files, exe_path=tmp_folder + "/exe"), shell=True)

    optimized_file = ""
    for filename in glob.glob(os.path.join(tmp_folder, '*.precodegen.*')):  
        optimized_file = filename
    result_ll = tmp_folder + "/result.ll"
    subprocess.check_output("llvm-dis {optimized_bc} -o {result_ll}".format(optimized_bc=optimized_file, result_ll=result_ll), shell=True)
    return result_ll
    
def compile_non_lto(source_files, optimization_level):
    tmp_folder = tempfile.mkdtemp()
    os.environ['LLVM_COMPILER'] = 'clang'
    exe_path = tmp_folder + "/exe"
    subprocess.check_output("wllvm++ -O{level} -g {source_files} -o  {exe_path}".format(level=optimization_level, source_files=source_files, exe_path=exe_path), shell=True)
    subprocess.check_output("extract-bc {exe_path}".format(exe_path=exe_path), shell=True)
    result_ll = tmp_folder + "/result.ll"
    subprocess.check_output("llvm-dis {exe_path} -o {result_path}".format(exe_path=exe_path + ".bc", result_path=result_ll), shell=True)
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
        match = re.match("(\![0-9]+).*filename: \"(.*\.cpp).*", source_file)
        if match:
            source_llvm_map[match.group(1)] = SourceFileConnect(match.group(2))
    for key in source_llvm_map.keys():
        matches = re.findall("(\![0-9]+).*file: {file}.*line: ([0-9]+).*".format(file=key), llvm_ir_output)
        for llvm_line, source_line  in matches:
            source_llvm_map[key].insert(source_line, llvm_line)
            color_line_map.insert(source_line)

    for values in source_llvm_map.values():
        new_values = []
        for scope_values in values.map.values():
            for scope_value in  scope_values:
                matches = re.findall("(\![0-9]+).*line: ([0-9]+).*scope: {scope}.*".format(scope=scope_value), llvm_ir_output)
                for llvm_line, source_line in matches:
                    new_values.append((source_line, llvm_line))
        for source_line, llvm_line in new_values:
            values.insert(source_line, llvm_line)
            color_line_map.insert(source_line)
        
       

    return source_llvm_map.values()

def generate_diff_string(llvm_ir, connected_files):
    result = ""
    string_list = llvm_ir.splitlines()
    string_list = string_list[2:]
    for line in string_list:
        is_found = False
        for connected_file in connected_files:
            for key, values in connected_file.map.items():
                for value in values :
                    match = re.search(".*\!dbg {value}.*".format(value=value), line)
                    if match:
                        curr_line = re.sub("\!dbg {value}.*".format(value=value), "", line)
                        curr_line = re.sub("%[0-9]+ = ", "", curr_line)
                        if curr_line[-2] == ",":
                            curr_line = curr_line[:-2]
                        result += connected_file.source_file_name + ":" + key + ":" + curr_line.lstrip()
                        is_found = True
                        encoded_real_instruction_map[connected_file.source_file_name + ":" + key + ":" + curr_line.lstrip()] = line
                        
        if not is_found:
            result += line
        result += "\n"       
    
    result = re.sub(";.*\n.*@llvm\.dbg\..*\n", "", result, re.MULTILINE)
    result = re.sub("; Function.*\n", "", result)
 
    result = re.sub(".*@llvm\.dbg\..*\n", "", result, re.MULTILINE)
    result = re.sub("attributes #[0-9]+ = .*", "", result, re.MULTILINE)
    return result
    

def parse_and_highlight_llvm(string_code, text_widget, connected_files, curr_source_file):
    for file in connected_files:
        if file.source_file_name == curr_source_file:
            curr_connected_file = file

    line_num = 1
    tag_num = 0
    string_list = string_code.splitlines()
    for code_line in string_list:
        for key, value_list in curr_connected_file.map.items():
                for value in value_list:
                    match = re.search(".*\!dbg {dbg_num}.*".format(dbg_num=value), code_line)
                    if match:
                        debug = re.search(".*@llvm\.dbg\..*", code_line)
                        if debug:
                            continue
                        llvm_debug_line_map[value] = True
                        text_widget.tag_add("start{}".format(tag_num),"{line_num}.5 linestart".format(line_num=line_num), "{line_num}.5 lineend".format(line_num=line_num) )
                        text_widget.tag_config("start{}".format(tag_num), background= "{}".format(color_line_map.map[key]), foreground= "black")
                        tag_num += 1

        line_num+=1

def parse_and_highlight_source(string_code, text_widget, connected_files, curr_source_file):
    connected_files_list = []

    for curr_connected in connected_files:
        for file in curr_connected:
            if file.source_file_name == curr_source_file:
                connected_files_list.append(file)

    line_num = 1
    tag_num = 0
    string_list = string_code.splitlines()
    for _ in string_list:
        for curr_connected_file in connected_files_list:
            if str(line_num) in curr_connected_file.map.keys():
                #if there is no that line in llvm, no need to highlight
                for val in curr_connected_file.map[str(line_num)] :
                    if val in llvm_debug_line_map:
                        text_widget.tag_add("start{}".format(tag_num),"{line_num}.5 linestart".format(line_num=line_num), "{line_num}.5 lineend".format(line_num=line_num) )
                        text_widget.tag_config("start{}".format(tag_num), background= "{}".format(color_line_map.map[str(line_num)]), foreground= "black")
                        tag_num += 1
                        break

        line_num+=1



def insert_text(non_lto_text_widget, string_non_lto, lto_text_widget, string_lto, connected_files, source_files, source_text_widget, label):
    global next_source_file_index
    next_source_file_index = next_source_file_index if next_source_file_index < len(source_files) else 0
    source_file_name = source_files[next_source_file_index]
    next_source_file_index +=1
    
    non_lto_text_widget.configure(state=tk.NORMAL)
    lto_text_widget.configure(state=tk.NORMAL)
    source_text_widget.configure(state=tk.NORMAL)

    non_lto_text_widget.delete("1.0","end")
    lto_text_widget.delete("1.0","end")
    source_text_widget.delete("1.0","end")
    label.config(text="Non LTO" + " " * 220 + source_file_name.split("/")[-1] + " " * (180  - len(source_file_name.split("/")[-1]))+ "LTO")

    non_lto_text_widget.insert(tk.END, string_non_lto)
    lto_text_widget.insert(tk.END, string_lto)
    source_file_text = read_file(source_file_name)
    source_text_widget.insert(tk.END, source_file_text)
    connected_lto, connected_non_lto = connected_files

    parse_and_highlight_llvm(string_lto, lto_text_widget, connected_lto, source_file_name)
    parse_and_highlight_llvm(string_non_lto, non_lto_text_widget, connected_non_lto, source_file_name)
    parse_and_highlight_source(source_file_text, source_text_widget, connected_files, source_file_name)

    non_lto_text_widget.configure(state=tk.DISABLED)
    lto_text_widget.configure(state=tk.DISABLED)
    source_text_widget.configure(state=tk.DISABLED)

def show_diff(lto_diff_file, non_lto_diff_file):
    file_diff, filename_diff = tempfile.mkstemp()
    temp = tempfile.NamedTemporaryFile()

    lto_diff_file.seek(0)
    lto_diff_string = lto_diff_file.read()
    non_lto_diff_file.seek(0)
    non_lto_diff_string = non_lto_diff_file.read()

    lto_diff_string = lto_diff_string.decode("utf-8")
    non_lto_diff_string = non_lto_diff_string.decode("utf-8")

    todate = file_mtime(lto_diff_file.name)
    fromdate = file_mtime(non_lto_diff_file.name)
    

    for line in difflib.unified_diff(non_lto_diff_string.splitlines(keepends=True),lto_diff_string.splitlines(keepends=True), 
                    fromfiledate=fromdate, tofiledate=todate, fromfile=non_lto_diff_file.name, tofile=lto_diff_file.name):
        if (line[0] == "+" or line[0] == "-") and (line[1] != "-" and line[1]!="+"):
            if line[1:-1] in encoded_real_instruction_map.keys():
                real_line = encoded_real_instruction_map[line[1:-1]] 
                line = line[0] + real_line + line[-1]
        temp.write(line.encode())

    temp.seek(0)
    #print(temp.read().decode("utf-8"))
    subprocess.check_output("kompare {out}".format(out=temp.name), shell=True)

def show_files(string_lto, string_non_lto, connected_files, source_files, lto_diff_file, non_lto_diff_file):
    root = tk.Tk()
    root.geometry("1800x700+200+150")
    non_lto_text = tk.Text(root, font=("times new roman",12))
    lto_text = tk.Text(root, font=("times new roman",12))
    source_file_text = tk.Text(root, font=("times new roman",12))
    button = tk.Button(root, text="Next source file", width=20, height=3, command=lambda: insert_text(non_lto_text, string_non_lto, lto_text, string_lto, connected_files, source_files, source_file_text, label))
    button_show_diff = tk.Button(root, height=3, width=20, text = "Show diff Non LTO - LTO", command=lambda: show_diff(lto_diff_file, non_lto_diff_file) )
    label = tk.Label(root, anchor="w")

    insert_text(non_lto_text, string_non_lto, lto_text, string_lto, connected_files, source_files, source_file_text, label)

    label.pack(side=tk.TOP, fill=tk.BOTH)
    non_lto_text.configure(state=tk.DISABLED)
    lto_text.configure(state=tk.DISABLED)
    lto_text.bind("<1>", lambda event: lto_text.focus_set())
    non_lto_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    non_lto_text.bind("<1>", lambda event: non_lto_text.focus_set())
    lto_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
    source_file_text.pack(fill=tk.BOTH, expand=True)
    source_file_text.configure(state=tk.DISABLED)
    button.pack()
    button_show_diff.pack()
    tk.mainloop()

def trim_debug_info(llvm_debug_otput):
    result = re.sub("^\![0-9]+ = .*\n", "", llvm_debug_otput, flags=re.MULTILINE)
    result = re.sub("^\!llvm\..*\n", "", result, flags=re.MULTILINE )
    return result.rstrip()

def compile_files(folder_path, optimization_level):
    source_files = ""
    for filename in glob.glob(os.path.join(folder_path, '*.cpp')):  
        source_files += filename + " "

    result_lto = compile_lto(source_files, optimization_level)
    result_non_lto = compile_non_lto(source_files, optimization_level)
    string_lto = read_file(result_lto)
    string_non_lto = read_file(result_non_lto)
    connected_files_non_lto = connect_source_llvm(string_non_lto)
    connected_files_lto = connect_source_llvm(string_lto)
    source_files_list = source_files.split()
    diff_file_non_lto = trim_debug_info(generate_diff_string(string_non_lto, connected_files_non_lto))
    diff_file_lto = trim_debug_info(generate_diff_string(string_lto, connected_files_lto))

    file_lto = tempfile.NamedTemporaryFile()
    file_non_lto = tempfile.NamedTemporaryFile()
    file_lto.write(diff_file_lto.encode())
    file_non_lto.write(diff_file_non_lto.encode())

    show_files(trim_debug_info(string_lto),trim_debug_info(string_non_lto), (connected_files_lto,connected_files_non_lto), source_files_list, file_lto, file_non_lto)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="Input folder path", required=True)
    parser.add_argument("-o", "--optimization_level", help= "Optimization level", nargs="?", type=str, const="0", default="0", choices=['0', '1', '2', '3', '4', 'z', 'g', 'z', 'fast'])
    args = parser.parse_args()
    compile_files(args.input, args.optimization_level)



