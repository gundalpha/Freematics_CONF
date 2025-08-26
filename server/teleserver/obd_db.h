//#pragma once
#ifndef __OBD_DB_H__
#define __OBD_DB_H__

#include "teleserver.h"
#ifdef POSTGRES_DB
#include <libpq-fe.h>
#endif


PGconn* connDb();

int InsertOBDMaster(CHANNEL_DATA* pld, char* payload);
int insertPidValue(int data_id, int pid, char *value);
void dbClose();
#endif // __OBD_DB_H__
