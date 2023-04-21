#include <stdio.h>
#include <stdlib.h>

__declspec(dllexport) int __cdecl install(int a, int b)
{
  FILE * f;
    char buffer[1035];

    // List of Macros/defines here: https://sourceforge.net/p/predef/wiki/Architectures/
#if defined(__amd64__)
    printf("Hello there from x86-64\n");   
#elif defined(__i386__)
    printf("Hello there from i386\n");       
#endif 

    system("C:\\Windows\\system32\\notepad.exe");

    f = popen("dir c:\\", "r");

    if (f == NULL) {
        printf("Command failed\n");
        return 1;
    }

    while (fgets(buffer, sizeof(buffer), f) != NULL) {
        printf("%s", buffer);
    }

    pclose(f);

    return 0;
}