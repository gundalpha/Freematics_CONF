//#pragma once
#ifndef __OBD_DB_H__
#define __OBD_DB_H__

#include "teleserver.h"
#ifdef POSTGRES_DB
#include <libpq-fe.h>
#endif


PGconn* connDb();

int InsertOBDMaster(CHANNEL_DATA* pld, char* payload, uint32_t trip_id, uint32_t ts);
int insertPidValue(int data_id, int pid, int iVal, float fVal, char *value);
int insertPidsValue(int data_id, int pid, char* value);
int insertPidiValue(int data_id, int pid, int iVal);
int insertPidfValue(int data_id, int pid, float fVal);
void dbClose();
#endif // __OBD_DB_H__
