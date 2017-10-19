#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <stdint.h>
#include <string.h>

#include <sys/io.h>
#include <sys/mman.h>

#define SLURP_TX_DATA           0x000
#define SLURP_TX_CTRL           0x180
#define SLURP_TX_MAIL           0x190
#define SLURP_TX_LEN            0x194
#define SLURP_RX_DATA           0x200
#define SLURP_RX_CTRL           0x380
#define SLURP_RX_MAIL           0x390
#define SLURP_RX_LEN            0x394

typedef uint32_t word_t;

word_t* request_iomem(uint32_t base, uint32_t len)
{
    int fd;
    word_t *iomem = NULL;

    fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (fd < 0) {
        printf("error: could not open MMIO file\n");
        return NULL;
    }

    iomem = (word_t *)mmap(NULL, len,
            PROT_READ | PROT_WRITE, MAP_SHARED, fd,
            base);
    if (iomem == MAP_FAILED) {
        printf("error: could not map iomem location\n");
        return NULL;
    }
    return iomem;
}

//int _recv_ethernet_frame()
//{
//    return 0;
//}

int _write_ethernet_frame(word_t *iomem, const char *buf, int len)
{
    if (iomem == NULL) {
        printf("iomem has not been mapped\n");
        return 0; }
    /* set the packet data */
    memcpy(&(iomem[SLURP_TX_DATA]), buf, len);
    /*  set the packet length */
    iomem[SLURP_TX_LEN] = len;
    /* not sure if these values are even important, but here they are */
    iomem[SLURP_TX_CTRL] = 0xa0000000;
    iomem[SLURP_TX_CTRL+1] = 0x02;
    return len; 
}

void _send_ethernet_frame(word_t *iomem)
{
    if (iomem == NULL) {
        printf("iomem has not been mapped\n");
        return; }
    /* wait until PL is ready for another packet */
    while (iomem[SLURP_TX_MAIL]);
    /* send the next packet */
    iomem[SLURP_TX_MAIL] = 0x01;
}
