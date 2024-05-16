import sys
import re
from faker import Faker
from config.db_info import DatabaseInfo
from sqlalchemy import Inspector
from util.utils import clean_console, print_menu, table_mapper, user_input
from util.database_utils import (
    insert_dummy_data,
    create_all_dummy,
    print_table,
    get_table_metadata,
    is_column_primary_key
)
from util.error.error_handler import exception_handler
from sqlalchemy.schema import CreateTable, MetaData


@exception_handler
def run(engine, fake: Faker, inspector: Inspector, db_info: DatabaseInfo):
    while True:
        clean_console()
        print_menu()
        choice = input("메뉴 입력: ")

        # 더미 데이터 생성
        if choice == '1':
            clean_console()
            num_records, mode, table_name = user_input(choice)
            if table_name in table_mapper().keys():
                dummy_data = table_mapper()[table_name](fake, num_records)
                insert_dummy_data(engine, table_name, dummy_data, mode)
                print("데이터를 정상적으로 적용했습니다.")
            else:
                print("올바른 테이블명을 입력해주세요.")

        elif choice == '2':
            clean_console()
            num_records, mode = user_input(choice)
            create_all_dummy(engine, fake, num_records, mode)

        elif choice == '3':
            clean_console()
            schema_inspector(engine, inspector, db_info)

        # 테스트 데이터 출력
        elif choice == '4':
            clean_console()
            table_name = input("테이블 이름을 정확히 입력해주세요: ")
            # 존재하지 않는 테이블을 가져왔다면
            if table_name not in table_mapper().keys():
                print("테이블 이름이 정확하지 않습니다")
            else:
                print_table(engine, table_name)

        elif choice == '5':
            clean_console()
            sys.exit(0)

        else:
            print("다시 입력해 주세요.")

        input("엔터를 누르면 초기화면으로 되돌아갑니다...")


def schema_inspector(engine, inspector: Inspector, db_info: DatabaseInfo):
    print("Database Management Menu")
    print("1. 현재 접속한 Database의 schema 목록")
    print("2. 현재 선택한 Schema에 속한 테이블 목록")
    print("3. 현재 선택한 Schema에 속한 뷰 목록")
    print("4. 현재 선택한 Schema에 속한 테이블 목록, 테이블 별 Column 정보, 코멘트 목록 조회")
    print("5. 현재 선택한 Schema에 속한 뷰 목록과 뷰 별 Column 정보, 코멘트 목록 조회")
    print("6. 특정 테이블의 Column 정보, Comment 조회")
    print("7. 특정 테이블의 DDL 스크립트 생성")
    menu = int(input("메뉴 입력 : "))

    if menu == 1:
        print(f"접속 정보 : {engine.url}")
        print(f"해당 접속에 대한 Schema 리스트 : {inspector.get_schema_names()}")

    elif menu == 2:
        print(f"현재 선택된 Schema : {db_info.database_name}")
        print(f"{db_info.database_name}에 속한 테이블 리스트 : {inspector.get_table_names(db_info.database_name)}")

    elif menu == 3:
        print(f"뷰 리스트 : {inspector.get_view_names(db_info.database_name)}")

    elif menu == 4:
        result = {}
        tables = inspector.get_table_names(db_info.database_name)
        for table in tables:
            # 아래 코드 리팩터링 필수
            columns = inspector.get_columns(table, db_info.database_name)
            column_dictionary = []
            for column in columns:
                column_details = {
                    'name': column['name'],
                    'type': str(column['type']),
                    'primary': is_column_primary_key(engine, table, column['name']),
                    'comment': column['comment'],
                    'default': column['default'],
                    'nullable': column['nullable'],
                    'autoincrement': column.get('autoincrement')
                }
                column_dictionary.append(column_details)
            result[table] = column_dictionary
        # 나중에 flask로 jsonify 사용하면 json으로 받을 수 있음
        for key, value in result.items():
            print(key, value)

    elif menu == 5:
        result = {}
        for view_name in inspector.get_view_names(db_info.database_name):
            # 정규식 사용은 CHAT GPT를 활용하였습니다.
            # 정규식: AS 'alias' 형식에서 alias만 추출
            re_aliases = re.findall(r'AS\s+`(\w+)`', inspector.get_view_definition(view_name))
            # 정규식: FROM 구문에서 테이블명 추출
            re_table_name = re.findall(r'FROM\s+`(\w+)`', inspector.get_view_definition(view_name), re.IGNORECASE)
            table_name = re_table_name[0]

            columns = inspector.get_columns(table_name, db_info.database_name)
            column_dictionary = []
            for column in columns:
                if column['name'] in re_aliases:
                    column_details = {
                        'name': column['name'],
                        'type': str(column['type']),
                        'primary': is_column_primary_key(engine, table_name, column['name']),
                        'comment': column['comment'],
                        'default': column['default'],
                        'nullable': column['nullable'],
                        'autoincrement': column.get('autoincrement')
                    }
                    column_dictionary.append(column_details)
            result[view_name] = column_dictionary

        for key, value in result.items():
            print(key, value)

    elif menu == 6:
        result = {}
        table_name = input("테이블 명 입력 : ")
        if table_name in table_mapper().keys():
            columns = inspector.get_columns(table_name, db_info.database_name)
            column_dictionary = []
            for column in columns:
                column_details = {
                    'name': column['name'],
                    'type': str(column['type']),
                    'primary': is_column_primary_key(engine, table_name, column['name']),
                    'comment': column['comment'],
                    'default': column['default'],
                    'nullable': column['nullable'],
                    'autoincrement': column.get('autoincrement')
                }
                column_dictionary.append(column_details)
            result[table_name] = column_dictionary
            print(result)
        else:
            print("올바른 테이블명을 입력해주세요.")
    elif menu == 7:
        # https://stackoverflow.com/questions/64677402/get-ddl-from-existing-databases-sqlalchemy
        meta = MetaData()
        meta.reflect(bind=engine)
        table_name = input('테이블 이름을 정확히 입력해주세요.')
        if table_name in table_mapper().keys():
            for table in meta.sorted_tables:
                if table.name == table_name:
                    print(CreateTable(table).compile(engine))
                    break