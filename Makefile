PYTHON := poetry run python

.PHONY: report

report:
	$(PYTHON) scripts/generate_report.py \
		$(if $(OAUTH_CLIENT),--oauth-client "$(OAUTH_CLIENT)",) \
		$(if $(GA4_CREDENTIALS),--credentials "$(GA4_CREDENTIALS)",) \
		$(if $(DEVELOPER_TOKEN),--developer-token "$(DEVELOPER_TOKEN)",) \
		$(if $(CUSTOMER_ID),--customer-id "$(CUSTOMER_ID)",) \
		$(if $(LOGIN_CUSTOMER_ID),--login-customer-id "$(LOGIN_CUSTOMER_ID)",)
