#include <stdio.h>
#include <stdlib.h>

int main() {
    FILE * f;
    char buffer[1035];

    // List of Macros/defines here: https://sourceforge.net/p/predef/wiki/Architectures/
#if defined(__amd64__)
    printf("Hello there from x86-64\n");   
#elif defined(__i386__)
    printf("Hello there from i386\n");       
#endif 


    printf("Running popen\n"); 
    f = popen("dir c:\\", "r");

    if (f == NULL) {
        printf("Command failed\n");
        return 1;
    }

    while (fgets(buffer, sizeof(buffer), f) != NULL) {
        printf("%s", buffer);
    }

    pclose(f);
    printf("Finishing popen\n");

    printf("Writing file\n");

    f = fopen("C:\\test.txt", "w+");

    if (f == NULL) {
        printf("File open failed failed\n");
        return 1;
    }

    fputs("Put in file data\n", f);
    fputs("Put in more file data\n", f);

    fclose(f);

    printf("Finished writing file\n");


    system("C:\\Windows\\system32\\notepad.exe");
    

    return 0;
}

