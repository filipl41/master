# master

## LTO_Compiler_explorer
Projekat je odradjen po ugledu na compiler explorer(https://godbolt.org/), stim sto ovde prikazujemo
razliku unutar izvrshih fajlova sa ukljucenom otpimizacijom tokom linkovanja i bez nje.
Takodje, slicno kao i u compiler explorer-u, oznacene su linije u llvm ir fajlovima koje odgovaraju
linijama u fajlovima izvornog koda. Istom bojom ce biti oznacene odgovarajuce linije u ovim fajlovima.
Klikom na dugme, menja se izvorni fajl i samim tim i obelezene linije unutar llvm ir fajlova.
Trenutno podrzani su iskljucivo programi pisani u programskom jeziku C++.
### Zahtevi
clang-9
wllvm
python3

### Primer pokretanja
python3 -i {path_to_dir_with_cpp_files} -o {optimization_level('0', '1', '2', '3', '4', 'z', 'g', 'z', 'fast)}

primer pokretanja "root" direktorijuma ovog projekta

python3 code/main.py  -i code/example/ -o 3

