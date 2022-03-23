#include <stdio.h>
#include <stdlib.h>

int main() {
    FILE * f;
    char buffer[1035];

    // List of Macros/defines here: https://sourceforge.net/p/predef/wiki/Architectures/
#if defined(__amd64__)
    printf("Hello there from x86-64\n");
#elif defined(__arm__)
    printf("Hello there from ARM32\n");
#elif defined(__aarch64__)
    printf("Hello there from ARM64\n");    
#elif defined(__i386__)
    printf("Hello there from i386\n");    
#elif defined(__mips64)
    printf("Hello there from MIPS64\n");    
#elif defined(__mips__)&&defined(__BYTE_ORDER__)&&(__BYTE_ORDER__ == __ORDER_BIG_ENDIAN__)
    printf("Hello there from MIPS32\n");    
#elif defined(__mips__)&&defined(__BYTE_ORDER__)&&(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__)
    printf("Hello there from MIPSEL32\n");    
#endif 

    system("touch /tmp/hello");

    f = popen("ls /", "r");

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

