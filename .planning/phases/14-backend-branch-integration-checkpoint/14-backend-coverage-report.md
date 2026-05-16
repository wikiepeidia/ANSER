# Phase 14 Backend Coverage Gate Report

- Timestamp (UTC): 2026-04-16T04:24:42.233970+00:00
- Status: passed
- Threshold: 20.0%
- Measured Coverage: 21.1%
- Exit Code: 0

## Command

```bash
C:\Users\wikiepeidia\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests/services tests/contracts -q --cov=app --cov=core --cov=routes --cov-config=.coveragerc --cov-report=term-missing:skip-covered --cov-fail-under=20.0
```

## Raw Output

```text
..............................                                           [100%]
=============================== tests coverage ================================
______________ coverage: platform win32, python 3.12.10-final-0 _______________

Name                                    Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------
app.py                                    224    102     34      1  47.7%   57-60, 69-87, 90-91, 94-101, 116-119, 200-202, 204, 211-225, 232-233, 252-256, 286-317, 322-347, 360-376
core\agent_middleware.py                   72     60     20      0  13.0%   11-20, 23-35, 39-70, 73-107, 110
core\auth.py                               62     49     12      0  17.6%   100-121, 124-129, 133-151, 156-177
core\automation_engine.py                 139    124     38      0   8.5%   13-18, 21-26, 29-87, 91-128, 132-168, 174-221
core\config.py                             24      1      2      1  92.3%   21->29, 25
core\database.py                          243    197     56     10  18.7%   16-18, 21-44, 47-49, 51->exit, 52->exit, 53->exit, 54->exit, 55->exit, 59-60, 61->exit, 62->exit, 63->exit, 64->exit, 72, 75-92, 96-101, 109-136, 163-168, 171-178, 181-189, 194-204, 208-227, 230-258, 262-271, 274-294, 297-314, 317-327, 330-361, 364-370
core\google_integration.py                317    297     88      0   4.9%   13-15, 38-183, 188-215, 222-274, 285-312, 318-344, 351-466, 472-497, 503-543
core\make_integration.py                   20     16      4      0  16.7%   9-34
core\models.py                             13      8      0      0  38.5%   16-22, 26
core\services\ai_chat_service.py           50     22     20      5  50.0%   14, 29, 35, 44-52, 62, 64, 83-89, 94-96
core\services\analytics_service.py         78     60     16      1  20.2%   25->exit, 29-30, 35-175
core\services\dl_client.py                133    120     52      1   7.6%   9->12, 18-20, 26-76, 83-141, 147-181
core\services\inventory_tx_service.py     123     49     32      6  58.1%   11, 16, 22, 56-67, 69->48, 84-89, 94-137, 172, 198, 206-208, 213-264
core\services\workflow_service.py          68     25     26      5  61.7%   15, 19-21, 36, 52-53, 69, 71, 100-110, 117-131
core\utils.py                              31     17      6      0  37.8%   7-9, 13-16, 21-38, 42-48, 52-58
core\workflow_engine.py                   302    275    142      4   7.0%   13-76, 98-104, 111-117, 120, 127-470
routes\ai_routes.py                       146    111     12      0  22.2%   25-27, 31-32, 36-40, 44-109, 116-154, 161-177, 183-193, 199-207, 213-222
routes\dl_routes.py                        55     41     10      0  21.5%   14-16, 23-41, 48-62, 69-94
routes\google_routes.py                   107     90     22      1  17.1%   10, 18-20, 30-33, 42-194, 201-234
routes\inventory_routes.py                 90     50      8      0  40.8%   23-40, 54-59, 68-86, 93-115, 134-139, 148-166
routes\main_routes.py                    1047    810    224      3  19.4%   15, 27-32, 38-41, 47, 52, 57-83, 88-122, 127-201, 206-233, 238->exit, 241, 269-283, 316-319, 325-328, 334-337, 343-348, 354-357, 364, 370, 376, 382, 388, 394, 401, 405->exit, 412-422, 428-452, 458-490, 496-525, 531-546, 552-577, 583-590, 595-601, 606-621, 626-631, 636-640, 645-648, 655-664, 679-683, 689-693, 706-728, 733-754, 760-771, 777-802, 809-906, 912-938, 980-993, 999-1042, 1048-1091, 1098-1105, 1112-1122, 1128-1144, 1150-1161, 1167-1172, 1179-1190, 1196-1212, 1218-1229, 1235-1240, 1247-1264, 1274-1284, 1290-1328, 1336-1358, 1370-1381, 1387-1407, 1413-1418, 1424-1436, 1442-1473, 1479-1515, 1521-1526, 1533-1564, 1571-1603, 1610-1696, 1702-1748, 1754-1837, 1843-1881
routes\wallet_routes.py                   276    236     66      1  13.2%   10, 17, 23-79, 85-87, 98-113, 119-143, 149-183, 191-249, 255-321, 327-349, 355-378, 384-426
routes\workflow_routes.py                  95     69      6      0  25.7%   16-18, 24-34, 40-51, 57-67, 73-85, 92-98, 105-134
-----------------------------------------------------------------------------------
TOTAL                                    3727   2829    896     39  21.0%

2 files skipped due to complete coverage.
Required test coverage of 20.0% reached. Total coverage: 21.05%
```

## Guidance

- Keep the threshold at or above the current pass line for merge preparation.
- Raise threshold gradually after each stabilization cycle.
