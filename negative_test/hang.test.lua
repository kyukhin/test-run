test_run = require('test_run').new()
test_run:cmd('create server replica with rpl_master=default, script="negative_tests/replica.lua"')
test_run:cmd('start server replica')
