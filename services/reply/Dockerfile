FROM python:3

WORKDIR /app

COPY services/reply/requirements.txt .
COPY shared/requirements.txt ./shared/requirements.txt

RUN pip3 install -r requirements.txt
RUN pip3 install -r shared/requirements.txt
RUN python -c "import demoji; demoji.download_codes()"