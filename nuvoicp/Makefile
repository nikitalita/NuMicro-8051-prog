CC = gcc
CFLAGS = -g -Wall -DPRINT_CONFIG_EN -DDYNAMIC_DELAY

#LDFLAGS = -lgpiod
DEV_OBJ = stub.o

default: all

all: nuvoicp shared
nuvoicp: main.o icp.o $(DEV_OBJ)
	$(CC) $(CFLAGS) -o nuvoicp $^
shared: main.o icp.o $(DEV_OBJ)
	$(CC) $(CFLAGS) -shared -o libnuvoicp-stub.so $^
test: itest.o icp.o $(DEV_OBJ)
	$(CC) $(CFLAGS) -o itest $^
clean:
	rm -f nuvoicp *.o libnuvoicp-*.so itest
