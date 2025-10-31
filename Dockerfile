FROM python:3.12

WORKDIR /code

COPY requirements.txt .

# Install the Microsoft ODBC Driver for SQL Server
# Deprecated apt-key method (do not use)
# RUN apt-get update && apt-get install -y curl gnupg && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
# 	curl -o /etc/apt/sources.list.d/mssql-release.list https://packages.microsoft.com/config/debian/11/prod.list && \
# 	apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17

# Modern method using gpg
RUN apt-get update && apt-get install -y curl gnupg && \
    mkdir -p /etc/apt/trusted.gpg.d && \
    curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft.gpg && \
    curl -o /etc/apt/sources.list.d/mssql-release.list https://packages.microsoft.com/config/debian/11/prod.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17

RUN apt-get update && apt-get install -y cronie \
	&& pip3 install -r requirements.txt

COPY . .

EXPOSE 50505

# ENTRYPOINT ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]

COPY mycron /etc/cron.d/mycron
RUN chmod 0644 /etc/cron.d/mycron

COPY start.sh .
RUN chmod +x start.sh
ENTRYPOINT ["./start.sh"]