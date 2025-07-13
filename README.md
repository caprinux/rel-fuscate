**Rel-fuscate** obfuscates ELF programs by modifying the `jmprel_entry->r_offset` value in JMPREL relocation table to result in functions resolving itself into another function's GOT entry, causing disassemblers and decompilers to display an incorrect imported function name.

This suite of scripts and proof of concept programs is based on the following [blog post](https://blog.elmo.sg/posts/breaking-disassembly-through-symbol-resolution).

**TODO** 

- [ ] deobfuscation script
