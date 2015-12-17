.PHONY: serve deploy serve-clean

serve:
	dev_appserver.py .

serve-clean:
	dev_appserver.py --clear_datastore=yes .

deploy:
	appcfg.py -A bluebonnets-test update .
