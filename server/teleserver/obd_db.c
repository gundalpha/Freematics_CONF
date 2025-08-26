#include "obd_db.h"
#include "teleserver.h"

#ifdef POSTGRES_DB
#include <libpq-fe.h>
PGconn* conn;
#endif  //POSTGRES_DB

extern PostgresParam postgresParam;
PGconn* connDb()
{
	char conninfo[256];
	printf(" host : %s, port = %d, id = %s, pass = %s, name = %s\n", 
		postgresParam.serverIP, postgresParam.serverPort, postgresParam.loginID,
		postgresParam.loginPass, postgresParam.dbName);
	sprintf(conninfo, "host='%s' port=%d user='%s'  password='%s' dbname='%s' ",
		postgresParam.serverIP, postgresParam.serverPort, postgresParam.loginID,
		postgresParam.loginPass, postgresParam.dbName);
	//const char* conninfo = "host='127.0.0.1' user='kiapicav' port=5432 dbname='kiapi_cav' password='kiapi5005!@#' ";
	/* 연결 열기 */
	printf("DB Conn -> %s\n", conninfo);

	conn = PQconnectdb(conninfo);
	if (PQstatus(conn) != CONNECTION_OK) {
		fprintf(stderr, "Connection to database failed : %s", PQerrorMessage(conn));
		PQfinish(conn);
		return (PGconn*)-1 ;
	}
	printf("Postgresql connection success...\n");
	return conn;
}

void dbClose()
{
	// 옜 옜
    PQfinish(conn);
}

//int InsertPidValue(uint16_t data_id, uint16_t pid, char* value)
int insertPidValue(int data_id, int pid, char* value)
{
	PGresult* res;
	//printf("%s: data_id:%d, PID:0x%x(%d), Value: %s\n", __FUNCTION__, data_id, pid, pid, value);
	if (!conn)
	{
		conn = connDb();
		// 연결 상태 확인
		if (PQstatus(conn) == CONNECTION_BAD) {
			fprintf(stderr, "데이터베이스 연결 실패: %s\n", PQerrorMessage(conn));
			PQfinish(conn);
			return -1;
		}
		else
		{
			;
			//printf("Postgresql make connection...\n");
		}
	}
	char sql[256];
	sprintf(sql, "INSERT INTO cavbase.tbl_obd_data (data_id, svc_mode_no, pid_dec, pid_hex, obd_data, rgst_dtm) "
		" VALUES(%d , '%s', %d , '%x' , '%s' , CURRENT_TIMESTAMP); ", 
		data_id, "1", pid, pid,  value);
		
	//printf("==> SQL: %s\n", sql);
	/* 쿼리문 실행 */
	res = PQexec(conn, sql);
	if (PQresultStatus(res) != PGRES_COMMAND_OK) {
		fprintf(stderr,"Query failed : %s", PQerrorMessage(conn));
		PQclear(res);
		return -1;
	}
	else
	{
		//printf("PID insert succesful\n");
		return 0;
	}
}

int InsertOBDMaster(CHANNEL_DATA* pld, char* payload)
{
	PGresult* res;
	if (!conn)
	{
		conn = connDb();
		// 연결 상태 확인
		if (PQstatus(conn) == CONNECTION_BAD) {
			fprintf(stderr, "데이터베이스 연결 실패: %s\n", PQerrorMessage(conn));
			PQfinish(conn);
			return -1;
		}
		else
		{
			;
			//printf("Postgresql make connection...\n");
		}
	}
	char sql[512];
	sprintf(sql, "INSERT INTO cavbase.tbl_obd_data_master(data_id, gatr_scn, vin, data_gatr_expl, rgst_dtm)"
		" values ( nextval('cavbase.seq_obd_data_mst_id'::regclass), '%s', '%s', '%s', current_timestamp )  RETURNING data_id ;",
		"1", pld->vin, payload);
	//printf("QSQL : %s\n", sql);
		
	/* 쿼리문 실행 */
	res = PQexec(conn, sql);
	if (PQresultStatus(res) != PGRES_TUPLES_OK) {
		fprintf(stderr, "Query failed : %s", PQerrorMessage(conn));
		PQclear(res);
		return -1;
	}
	else
	{
		//printf("Add new raw completed...");
		
		/* 쿼리문 실행 */
		char *data_id = PQgetvalue(res, 0, 0);
		printf("Inserted data_id=%s\n", data_id);
		
		return atoi(data_id);
	}
	
}
