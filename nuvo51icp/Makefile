CC = gcc
CFLAGS = -g -Wall -DPRINT_CONFIG_EN

#LDFLAGS = -lgpiod
DEV_OBJ = stub.o

default: all

all: nuvo51icp shared
nuvo51icp: main.o n51_icp.o device_common.o $(DEV_OBJ)
	$(CC) $(CFLAGS) -o nuvo51icp $^
shared: main.o n51_icp.o device_common.o $(DEV_OBJ)
	$(CC) $(CFLAGS) -shared -o libnuvo51icp-stub.so $^
test: itest.o n51_icp.o device_common.o $(DEV_OBJ)
	$(CC) $(CFLAGS) -o itest $^
clean:
	rm -f nuvo51icp *.o libnuvo51icp-*.so itest
