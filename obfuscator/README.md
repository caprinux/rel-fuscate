You can find a more detailed walkthrough on how to use this [here](https://blog.elmo.sg/posts/breaking-disassembly-through-symbol-resolution/#the-scuffed-result).

1. Compile your program **without the header file** once with the following `gcc` flags: `-Wl,-z,relro,-z,lazy`  _(ensure partial relro)_
2. Run `get_imports.py` to get the list of imported functions.
3. Now that we have a list of the functions used by the program, we can re-compile the program **with the header file** by adding `#include "relfuscate.h"`.
  - You might need to add some libraries when compiling depending on the random functions that you have in your `relfuscate.h`. The one provided above would require `-lm -ldl -lpthread -lcrypt -lrt -lutil -lresolv -lnsl -lselinux -lcrypto`. _(p.s. you should also add `-w` to supress warnings for your sanity!)_
4. To remove the unnecessary code, you can run `objcopy --remove-section ".fun" program.elf`
5. Now we will run `relfuscate.py` and paste the list of imported used functions obtained from `get_imports.py`, and we are done!
