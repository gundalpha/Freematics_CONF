-- -------------------------------------------------------------------------------------
--      OBD 데이터 등록 Table
-- -------------------------------------------------------------------------------------

-- cavbase.tbl_obd_data_master definition
CREATE SEQUENCE cavbase.seq_obd_data_mst_id;
CREATE TABLE cavbase.tbl_obd_data_master ( 
	data_id			int8 DEFAULT nextval('cavbase.seq_obd_data_mst_id'::regclass) NOT NULL, 
	gatr_scn			int2 DEFAULT 1 NOT NULL, 
	vin					varchar(17) NOT NULL, 
	data_gatr_expl	varchar DEFAULT 'NORMAL'::character varying NOT NULL, 
	rgst_dtm			timestamp NOT NULL, 
CONSTRAINT "PK_tbl_obd_data_master" PRIMARY KEY (data_id)
);

COMMENT ON TABLE cavbase.tbl_obd_data_master IS 'OBD 데이터의 1 turn 조회를 구분하는 정보 테이블';

-- Column comments
COMMENT ON COLUMN cavbase.tbl_obd_data_master.data_id IS '차량 OBD 데이터의 1 turn 조회 번호(Auto)
(1회 조회에 대한 대표 PK번호 - 여러개 PID가 포함될 수 있음) ';
COMMENT ON COLUMN cavbase.tbl_obd_data_master.gatr_scn IS '1 = 자동(OBD 설정)
2 = 조회(특정 PID요청)';
COMMENT ON COLUMN cavbase.tbl_obd_data_master.vin IS '차대번호';
COMMENT ON COLUMN cavbase.tbl_obd_data_master.data_gatr_expl IS '차량 OBD 데이터의 1 turn 조회에 대한 설명 내용';
COMMENT ON COLUMN cavbase.tbl_obd_data_master.rgst_dtm IS '등록 일시';

-- Constraint comments
COMMENT ON CONSTRAINT "PK_tbl_obd_data_master" ON cavbase.tbl_obd_data_master IS 'OBD Data 마스터 기본키';

-- Permissions
ALTER TABLE cavbase.tbl_obd_data_master OWNER TO kiapicav;
GRANT ALL ON TABLE cavbase.tbl_obd_data_master TO kiapicav;


-- cavbase.tbl_obd_data definition

CREATE TABLE cavbase.tbl_obd_data ( 
	data_id			int8 NOT NULL, 
	svc_mode_no	int4 NOT NULL, 
	pid_dec			int4 NOT NULL, 
	pid_hex			bytea NULL, 
	obd_bin_data	bytea NULL, 
	obd_data			varchar NOT NULL, 
	rgst_dtm			timestamp NOT NULL, 
CONSTRAINT "PK_tbl_obd_data" PRIMARY KEY (data_id, svc_mode_no, pid_dec), 
CONSTRAINT "FK_tbl_obd_data_master_TO_tbl_obd_data" FOREIGN KEY (data_id) REFERENCES cavbase.tbl_obd_data_master(data_id)
);

COMMENT ON TABLE cavbase.tbl_obd_data IS 'OBD-II 단자에서 취득한 차량 데이터를 적재하는 테이블';

-- Column comments
COMMENT ON COLUMN cavbase.tbl_obd_data.data_id IS '데이터 ID';
COMMENT ON COLUMN cavbase.tbl_obd_data.svc_mode_no IS '서비스 모드 번호';
COMMENT ON COLUMN cavbase.tbl_obd_data.pid_dec IS 'OBD-II PID 번호(Decimal)';
COMMENT ON COLUMN cavbase.tbl_obd_data.pid_hex IS 'OBD-II PID 번호(HEX)';
COMMENT ON COLUMN cavbase.tbl_obd_data.obd_bin_data IS 'OBD 데이터 값(Binary)';
COMMENT ON COLUMN cavbase.tbl_obd_data.obd_data IS 'OBD DATA';
COMMENT ON COLUMN cavbase.tbl_obd_data.rgst_dtm IS '등록일시';

-- Constraint comments
COMMENT ON CONSTRAINT "PK_tbl_obd_data" ON cavbase.tbl_obd_data IS 'OBD Data 기본키';
COMMENT ON CONSTRAINT "FK_tbl_obd_data_master_TO_tbl_obd_data" ON cavbase.tbl_obd_data IS 'OBD Data 마스터 -> OBD Data';

-- Permissions
ALTER TABLE cavbase.tbl_obd_data OWNER TO kiapicav;
GRANT ALL ON TABLE cavbase.tbl_obd_data TO kiapicav;