.PHONY: serve deploy serve-clean test

serve:
	dev_appserver.py .

serve-clean:
	dev_appserver.py --clear_datastore=yes .

deploy:
	appcfg.py -A txbb-points update .

deploy-test:
	appcfg.py -A bluebonnets-test update .

test:
	python run_tests.py ~/lib/google_appengine tests
