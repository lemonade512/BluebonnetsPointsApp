.PHONY: serve deploy

serve:
	dev_appserver.py .

deploy:
	appcfg.py -A bluebonnets-test update .
