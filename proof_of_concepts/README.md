# Spoofing reloc_arg values

[poc_reloc_arg.elf](./poc_reloc_arg.elf)

This PoC is created by compiling the following program

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
  exit(0); // patched reloc_arg to act as sleep
  puts("hello world!");
  alarm(0); // patched reloc_arg to act as exit

  sleep(0); // we leave this inside just to include it as an import
}
```

and patching the `reloc_arg` in the PLT stubs.

```diff
  .plt:0000000000401040                 endbr64
- .plt:0000000000401044                 push    1 // alarm reloc_arg
+ .plt:0000000000401044                 push    2 // exit reloc_arg
  .plt:0000000000401049                 bnd jmp sub_401020
  
  .plt:0000000000401050                 endbr64
- .plt:0000000000401054                 push    2 // exit reloc_arg
+ .plt:0000000000401054                 push    3 // sleep reloc_arg
  .plt:0000000000401059                 bnd jmp sub_401020
```

# Writing into other GOT entries by spoofing r_offset values 

[poc_r_offset.elf](./poc_r_offset.elf)

This PoC is created by compiling the following program

```c
// gcc -Wl,-z,relro,-z,lazy  test.c -o poc_r_offset

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
        sleep(0); // shows up as exit(0)
        puts("hello world!");
        exit(0);
}

void* __attribute__((used)) dummy() {
        void* a = malloc(0);
        return a;
}
```

and patching the JMPREL Relocation table

```diff
  LOAD:0000000000000670                 Elf64_Rela <4018h, 300000007h, 0> ; R_X86_64_JUMP_SLOT puts
- LOAD:0000000000000688                 Elf64_Rela <4020h, 500000007h, 0> ; R_X86_64_JUMP_SLOT malloc
- LOAD:00000000000006A0                 Elf64_Rela <4028h, 600000007h, 0> ; R_X86_64_JUMP_SLOT exit
- LOAD:00000000000006B8                 Elf64_Rela <4030h, 800000007h, 0> ; R_X86_64_JUMP_SLOT sleep
+ LOAD:0000000000000688                 Elf64_Rela <4028h, 500000007h, 0> ; R_X86_64_JUMP_SLOT malloc
+ LOAD:00000000000006A0                 Elf64_Rela <4030h, 600000007h, 0> ; R_X86_64_JUMP_SLOT exit
+ LOAD:00000000000006B8                 Elf64_Rela <4020h, 800000007h, 0> ; R_X86_64_JUMP_SLOT sleep
```

# r3kapig CTF challenge

This was a maze generation challenge created for [R3CTF](https://ctftime.org/event/2731) organized by [r3kapig](https://r3kapig.com/).

The source code can be found [here](./r3ctf_maze_generator_challenge.c) and the program can be found [here](./r3ctf_maze_generator_challenge.elf).

- The real program functionality is revealed when any 6 additional arguments are passed to the program.
- Determines the maze seed by doing a SHA256 hash of the ELF file in memory _(this will catch any breakpoints or patching)_
- Anti-debugging by checking parent process name, and checking ptrace return value
- Generates maze with Kruskal algorithm, allowing participant to input a hex stream that is converted into a series of steps in the maze _(every 2 bits is one step)_.
