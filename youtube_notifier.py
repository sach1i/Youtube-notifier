from googleapiclient.discovery import build
import time
import datetime
import smtplib


def send_notification(ch, vid, link):
    # THE MESSAGE
    body = f'The channel: {ch} uploaded today following video "{vid}", link: {link}'
    # ESTABLISH CONNECTION WITH GMAIL
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    # LOGIN
    # SENDER MAIL
    sender = ''
    # APP PASSWORD FOR THE ACCOUNT HAS TO BE REQUESTED FROM GOOGLE
    app_pass = ''
    # LOG IN SO APP CAN SEND MESSAGES ON YOUR BEHALF
    server.login(sender, app_pass)
    subject = '!NEW VIDEOS!'
    # MESSAGE
    msg = f'Subject:{subject}\n\n{body}'
    receiver_mail = ''
    # SENDING MAIL
    server.sendmail(
        sender,
        receiver_mail,
        # ENCODONG FOR AVOIDING PROBLEMS WITH INTERPRETATION OF UNICODE AND UTF-8
        msg.encode()
    )
    print('Notification has been sent!')
    server.quit()


def get_amount_of_pages(total_subs):
    if total_subs < 50:
        number_of_pages = 1
    elif (total_subs % 50) == 0:
        number_of_pages = total_subs / 50
    elif (total_subs % 50) > 0:
        number_of_pages = (total_subs // 50) + 1
    return number_of_pages


if __name__ == '__main__':
    # YOUR API KEY HERE
    api_key = ''

    # MAIN METHOD TO WORK WITH YOUTUBE API
    youtube = build('youtube', 'v3', developerKey=api_key)

    # YOUR CHANNEL ID
    channel_id = ''
    # DEFAULT YOUTUBE FORMATTED WATCH LINK TO ADD VIDEO IDs LATER
    youtube_watch_link = 'https://www.youtube.com/watch?v='

    # GET ALL SUBSCRIPTIONS OF GIVEN CHANNEL IN JSON FORMAT
    request = youtube.subscriptions().list(part='snippet', channelId=channel_id, maxResults=50)
    response = request.execute()

    # GET AMOUNT OF PAGES OF RESULTS
    # (how many pages of the size 50 of subscriptions are there, e.g. 120 subscriptions = 3 pages)
    pages = get_amount_of_pages(response['pageInfo']['totalResults'])

    # EMPTY LIST TO BE FILLED LATER TO MERGE SUBSCRIPTIONS FROM ALL PAGES
    all_subs = []
    # LIST OF DICTIONARIES WHICH SHOULD REPRESENT EACH PAGE OF SUBSCRIPTIONS RESPECTIVELY
    page_subs = []
    for i in range(pages):
        page_subs.append({})

    # FILL IN FIRST PAGE, GETS ONLY PART OF RESPONSE FROM WHICH WE CAN EXTRACT NECESSARY DATA FOR LATER USE
    for key in response:
        if key == 'items':
            page_subs[0] = response[key]
    # SAME AS PROCESS ABOVE BUT FOR CASE OF SEVERAL PAGES
    if pages > 1:
        # TOKEN NEEDS TO BE PASSED IN ORDER TO ACCESS THE NEXT PAGE, OTHERWISE FIRST PAGE IS ACCESSED
        next_token = response['nextPageToken']
        counter = pages - 1
        for i in range(counter):
            request = youtube.subscriptions().list(part='snippet', channelId=channel_id, maxResults=50,
                                                   pageToken=next_token)
            response = request.execute()
            for key in response:
                if key == 'items':
                    # ASSIGN NEXT PAGE TO THE NEXT RESERVED LIST
                    page_subs[i + 1] = response[key]
            # LAST PAGE DOESN'T HAVE TOKEN. HENCE I LOOK FOR TOKENS ONLY IF PAGE ISN'T LAST
            if counter - i != 1:
                next_token = response['nextPageToken']

    # MERGE SUBS FROM ALL PAGES TO ONE PLACE
    for i in range(pages):
        all_subs.extend(page_subs[i])

    # CHANNELS' NAMES AND THEIR RESPECTIVE IDs ARE KEPT HERE
    channels = {}
    for i in range(len(all_subs)):
        ch_title = all_subs[i]['snippet']['title']
        ch_Id = all_subs[i]['snippet']['resourceId']['channelId']
        channels[ch_title] = ch_Id

    # CHANNELS' NAMES AND THEIR RESPECTIVE 'UPLOAD' PLAYLISTS
    uploads = {}
    for channel in channels:
        request = youtube.channels().list(part='contentDetails', id=channels[channel])
        response = request.execute()
        for key in response:
            if key == 'items':
                keep = response[key]
                uploads[channel] = keep[0]['contentDetails']['relatedPlaylists']['uploads']

    # I OPEN TOO MANY CONNECTIONS TOO FAST, SERVER WAS REFUSING TO CONNECT, HENCE A PAUSE
    time.sleep(5)

    # ONLY TODAY'S VIDEOS ARE CONSIDERED AS 'FRESH'
    fresh_videos = {}
    for channel in uploads:
        request = youtube.playlistItems().list(part='snippet', playlistId=uploads[channel], maxResults=3)
        response = request.execute()
        for key in response:
            if key == 'items':
                keep = response[key]
                # IF CHANNELS' UPLOADS ARE NOT EMPTY
                if len(keep) != 0:
                    # GET TIME FROM RESPONSE AND CONVERT TO DATE OBJECT
                    published = keep[0]['snippet']['publishedAt']
                    published = datetime.datetime.strptime(published[:10], '%Y-%m-%d').date()
                    # IF VIDEO WAS UPLOADED TODAY, ADD IT TO FRESH VIDEOS
                    if published == datetime.date.today():
                        vid_title = keep[0]['snippet']['title']
                        vid_Id = keep[0]['snippet']['resourceId']['videoId']
                        fresh_videos[channel] = [vid_title, vid_Id]
                    else:
                        break
                else:
                    continue

    # IF THERE ARE FRESH VIDEOS, SEND NOTIFICATIONS
    if len(fresh_videos) != 0:
        for channel in fresh_videos:
            link = youtube_watch_link + fresh_videos[channel][1]
            send_notification(channel, fresh_videos[channel][0], link)
