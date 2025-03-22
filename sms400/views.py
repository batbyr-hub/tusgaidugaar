# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from sms400.models import *
from datetime import datetime
import logging
from rest_framework.decorators import api_view
import json, requests
from django.http import HttpResponse
import re
import time
from rest_framework.parsers import JSONParser
from django.http.response import JsonResponse
from rest_framework import status
from .forms import UploadFileForm, FileUpload
import openpyxl
from django.shortcuts import render

# import numpy as np

log_date = datetime.now().strftime('%Y-%m-%d')
log_file = 'C:/Users/batuu/OneDrive/Documents/Self-employed/Projects/tusgaidugaar/log/Log_{0}'.format(log_date)
logging.basicConfig(filename=log_file + '.log', level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s')

print("This is my local version")

# Create your views here.
@api_view(['GET'])
def receive_sms(request):
    sms_from = request.query_params.get('sms_from', None)
    sms_text = request.query_params.get('sms_text', None)
    logging.info(sms_from)
    logging.info(sms_text)
    userMessage = UserMessage400()
    userMessage.sms_from = sms_from
    userMessage.sms_to = "400"
    userMessage.sms_text = sms_text
    result = ""
    if EmployeeNumber.objects.filter(number=sms_from, status='A').exists():
        if len(sms_text) == 10:
            text = sms_text[:2].upper() + sms_text[2:]
            if re.search('[а-яА-Я]{2}', text) and re.search('[0-9]{8}', text) and len(text) == 10:
                res = checkUser(text)
                logging.info("res")
                logging.info(len(res))
                if NewUser400.objects.filter(register=sms_text[:10]).exists():
                    n = str(NewUser400.objects.get(register=sms_text[:10]).number)
                    nn = str(n[:4]) + "****"
                    result = "Ene xereglegch {0} dugaar deer burtgeltei baina.".format(nn)
                    sta = "1"
                    userMessage.sms_response = result
                elif len(res) == 0:
                    # logging.info("len(res)==0")
                    result = "Xereglegch oldsongui."
                    sta = "0"
                    userMessage.sms_response = result
                else:
                    active = []
                    postpaid = []
                    oneway = []
                    twoway = []
                    for i in range(len(res)):
                        s = str(json.loads(res[i]["ACC_NBR"]))
                        ss = s[:4] + "****".encode('utf-8')
                        if res[i]["POSTPAID"] == "Y":
                            postpaid.append(ss)
                        elif res[i]["POSTPAID"] == "N":
                            if res[i]["PROD_STATE"] == "A":
                                active.append(ss)
                            if res[i]["PROD_STATE"] == "D":
                                oneway.append(ss)
                            if res[i]["PROD_STATE"] == "E":
                                twoway.append(ss)
                    if len(postpaid) != 0:
                        sendSms(sms_from, "DT-" + str(postpaid))
                    if len(active) != 0:
                        sendSms(sms_from, "UT active-" + str(active))
                    if len(oneway) != 0:
                        sendSms(sms_from, "UT oneway-" + str(oneway))
                    if len(twoway) != 0:
                        sendSms(sms_from, "UT twoway-" + str(twoway))
                    sta = "0"
                    if len(res) < 600:
                        userMessage.sms_response = str(postpaid) + " " + str(active) + " " + str(oneway) + " " + str(
                            twoway)
                    else:
                        userMessage.sms_response = ""
            else:
                result = "Tany xuselt amjiltgui bolloo. Registeriin dugaaraa daxin ilgeej shalgana uu."
                sta = "1"
                userMessage.sms_response = result
        elif sms_text.split(" ")[0] and sms_text[11:].isnumeric():
            register = sms_text[:2].upper() + sms_text[2:10]
            if re.search('[а-яА-Я]{2}', register) and re.search('[0-9]{8}', register) and len(register) == 10:
                if NewUser400.objects.filter(register=register).exists():
                    result = "Ene xereglegch {0} dugaar deer burtgeltei baina.".format(
                        NewUser400.objects.get(register=sms_text[:10]).number)
                    sta = "1"
                    userMessage.sms_response = result
                else:
                    if NewUser400.objects.filter(number=sms_text[11:], status=3).exists():
                        newUser = NewUser400.objects.get(number=sms_text[11:], status=3)
                        newUser.register = register
                        newUser.received_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        newUser.save()
                        result = "Hereglegchiin medeeleliig amjilttai shinechillee."
                    else:
                        newUser = NewUser400()
                        newUser.sms_from = sms_from
                        newUser.register = register
                        newUser.number = sms_text[11:]
                        newUser.received_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        newUser.status = "1"
                        newUser.serial = ""
                        newUser.nuhtsul = ""
                        newUser.location = ""
                        newUser.save()
                        result = "Xereglegchiin medeelel amjilttai bvrtgegdlee."
                    sta = "0"
                    userMessage.sms_response = result
            else:
                result = "Tany xuselt amjiltgui bolloo. Registeriin dugaaraa daxin ilgeej shalgana uu."
                sta = "1"
                userMessage.sms_response = result
        else:
            res = sendSms(sms_from, "Uuchlaarai, tany ilgeesen utga buruu baina.")
            time.sleep(2)
            if res == "0: Accepted for delivery":
                sendSms(sms_from,
                        "Burtgeltei dugaartai esexiig shalgax bol: Registeriin dugaar, Xereglegch burtguulex bol: Registeriin dugaar + Utasny dugaar gesen utgyg ilgeene uu.")
            sta = "1"
            userMessage.sms_response = result
    else:
        result = "Uuchlaarai, tany dugaar burtgelgui baina. Dugaaraa burtguulne uu."
        sta = "2"
        userMessage.sms_response = result

    userMessage.received_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    userMessage.status = sta
    userMessage.save()
    logging.info("userMessage.sms_response: " + str(userMessage.sms_response))
    return HttpResponse(result)


def checkUser(register):
    logging.info("checkUser")
    url = "http://192.168.18.105:8080/index.php/billing/check"
    headers = {'content-type': 'application/json'}
    da = {
        "register": register
    }
    res = requests.post(url, data=json.dumps(da), headers=headers)
    result = json.loads(res.text)
    logging.info(result)
    return result


def sendSms(number, smsText):
    url = "http://192.88.80.195/cgi-bin/sendsms?username=rd_search&password=search*0422&from=400&to=" + str(
        number) + "&text=" + str(smsText)
    hariu = requests.get(url)
    return hariu.content


@api_view(['POST'])
def toOdko(request):
    logging.info("toOdko")
    if request.method == 'POST':
        data = JSONParser().parse(request)
        register = data["register"]
        logging.info(register)
        if re.search('[а-яА-Я]{2}', register) and re.search('[0-9]{8}', register) and len(register) == 10:
            res = checkUser(register)
            if len(res) == 0:
                if NewUser400.objects.filter(register=register).exists():
                    stat = "unsuccessful"
                else:
                    logging.info("nad deer burtgeltei")
                    stat = "successful"
            else:
                logging.info("billing deer burtgeltei")
                stat = "unsuccessful"
        else:
            logging.info("buruu register")
            stat = "unsuccessful"
        response = {
            "status": stat
        }
        return JsonResponse(response, status=status.HTTP_200_OK)


@api_view(['POST'])
def toZaya(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        number = data["number"]
        ownerNumber = ""
        if NewUser400.objects.filter(number=number).exists():
            stat = "successful"
            ownerNumber = NewUser400.objects.get(number=number).sms_from
        else:
            logging.info("nad deer burtgeltei")
            stat = "unsuccessful"
        response = {
            "status": stat,
            "ownerNumber": ownerNumber
        }
        return JsonResponse(response, status=status.HTTP_200_OK)


@api_view(['POST'])
def newUserRegister(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        sms_from = data["sms_from"]
        register = data["register"]
        number = data["number"]
        if NewUser400.objects.filter(register=register).exists():
            text = "Ene hereglegch {0} dugaar deer burtgeltei baina".format(
                NewUser400.objects.get(register=register).number)
            stat = "success"
        else:
            newUser = NewUser400()
            newUser.sms_from = sms_from
            newUser.register = register
            newUser.number = number
            newUser.received_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            newUser.status = "2"
            newUser.save()
            text = "Burtgelgui hereglegch tul systemd burtgelee"
            stat = "success"
        response = {
            "status": stat,
            "text": text
        }
        return JsonResponse(response, status=status.HTTP_200_OK)


def uploadExcel(request):
    if request.method == 'GET':
        f = FileUpload()
    elif request.method == 'POST':
        f = FileUpload(request.POST, request.FILES)
    return render(request, 'upload.html', {'form': f})


def upload(request):
    f = FileUpload(request.POST, request.FILES)
    if f.is_valid():
        uploaded_file = f.cleaned_data['file']
        wbFormulas = openpyxl.load_workbook(uploaded_file)
        sheet = wbFormulas.active
        i = 1
        while sheet["A" + str(i)].value != None:
            sms_from = str(sheet["A" + str(i)].value)
            number = str(sheet["B" + str(i)].value)
            status = str(sheet["C" + str(i)].value)
            serial = str(sheet["D" + str(i)].value)
            location = str(sheet["E" + str(i)].value)

            newUser = NewUser400()
            newUser.sms_from = sms_from
            newUser.number = number
            newUser.status = status
            newUser.serial = serial
            newUser.nuhtsul = ""
            newUser.location = location
            newUser.save()
            i = i + 1
    context = {"error1": "Amjilttai"}
    return render(request, 'timeout.html', context)
