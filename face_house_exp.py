
from psychopy import visual, core, data, event, monitors, gui, misc, sound, logging
import numpy as np
import os, glob, sys
import datetime
#import matplotlib.pyplot as plt
from timeit import default_timer as t_timer   
import shutil
#from psychopy.hardware import crs
import random

random.seed(2024)
np.random.seed(2024)


def get_image(imgType='face', imgNumber = 0, imgSize=(256,256)):
    ''' Pick up a file, collapse 3rd dimension if it exists, and
    return a square chunk
    
    Usage examples for PIL copied from 
    https://www.geeksforgeeks.org/python-pil-image-resize-method/
    '''
    directory = os.path.join('images', imgType)
    #img_files = glob.glob(os.path.join(directory, '*.png'))
    #img = random.choice(img_files)
    img = os.path.join(directory, f'{imgType}_{imgNumber}.png')
    
    from PIL import Image 
    # Opens a image in RGB mode 
    im1 = Image.open(img)
    # make it square
    width, height = im1.size 
    if width < height:
        im1 = im1.crop((0, 0, width, width))
    elif height < width:
        im1 = im1.crop((0, 0, height, height))
    im1 = np.array(im1.resize(imgSize))
    if len(im1.shape) > 2:
        im1 = np.mean(im1, axis=2)
    im1 = im1[-1::-1, :]/128. - 1.
    return im1, os.path.basename(img)

def blended_image(alpha):
    image_1, _ = get_image(imgType='face')
    image_2, _ = get_image(imgType='house')
    blended = image_1 * (1.0 - alpha) + image_2 * alpha
    return blended 

def wait_for_button_press(keys, timer, onset_time=0, rList=None, oFile=None):
    ''' we do this a lot, and it takes up a lot of space
    '''
    # We've had a hard time in the past with wrong presses from the last 
    # trial being used in this trial
    event.clearEvents()
    # here's our chance to let someone end and save
    quitKeys = ['escape'] 
    gotAnswer = False
    response = []
    while (not gotAnswer):
        kbCheck = event.getKeys()
        if kbCheck:
            gotAnswer = True
            if kbCheck[0] in quitKeys:
                window.close()
                if rList and oFile:
                    saveResponses(rList, oFile)
                core.quit()
            elif kbCheck[0] in keys:
                response = kbCheck[0]
            else:
                # ignore accidental key presses
                gotAnswer = False
    return response, timer.getTime() - onset_time
                
def saveResponses(responseList, fileName):
    with open(fileName, 'w+') as fid:
        fid.write('blockType, iTrial, trialOnset, rampOnset, noiseOnset, promptOnset, noisePercept, noiseRT, im_house_fileName, im_face_fileName\n')
        for trial in responseList:
            # Check if both image file names are available
            if 'im_house_fileName' in trial and 'im_face_fileName' in trial:
                fid.write('%s, %d, %.3f, %.3f, %.3f, %.3f, %s, %.3f, %s, %s\n' \
                    %(  subjInfo['blockType'],
                        trial['iTrial'],
                        trial['trialOnset'],
                        trial['rampOnset'],
                        trial['noiseOnset'],
                        trial['promptOnset'],
                        trial['noisePercept'],
                        trial['noiseRT'],
                        trial['im_house_fileName'],
                        trial['im_face_fileName']))
            # Check if only im_house_fileName is available
            elif 'im_house_fileName' in trial:
                fid.write('%s, %d, %.3f, %.3f, %.3f, %.3f, %s, %.3f, %s, None\n' \
                    %(  subjInfo['blockType'],
                        trial['iTrial'],
                        trial['trialOnset'],
                        trial['rampOnset'],
                        trial['noiseOnset'],
                        trial['promptOnset'],
                        trial['noisePercept'],
                        trial['noiseRT'],
                        trial['im_house_fileName']))
            # Check if only im_face_fileName is available
            elif 'im_face_fileName' in trial:
                fid.write('%s, %d, %.3f, %.3f, %.3f, %.3f, %s, %.3f, None, %s\n' \
                    %(  subjInfo['blockType'],
                        trial['iTrial'],
                        trial['trialOnset'],
                        trial['rampOnset'],
                        trial['noiseOnset'],
                        trial['promptOnset'],
                        trial['noisePercept'],
                        trial['noiseRT'],
                        trial['im_face_fileName']))


### Get subject, file-saving info
subjInfo = {'Subject ID': 'pnr','blockType': ['attn_face', 'attn_house', 'only_face', 'only_house'],
            'run #': ["1", "2", "3", "4"]}
infoDlg = gui.DlgFromDict(dictionary=subjInfo,
                          title='runInfo',
                          order =['Subject ID','blockType', 'run #']
                          )


print(subjInfo)
if infoDlg.OK:
    print(subjInfo)
else:
    print('User cancelled')
    core.quit()

responseKeys = ['r', 'g', 'b', 'y', '1', '2', '3', '4']
triggerKeys = ['t', '5']
# get a timestamp to save the file so we don't overwrite anything
nowTime = datetime.datetime.now()
timeStamp = '%04d%02d%02d_%02d%02d' %(nowTime.year,
                                        nowTime.month,
                                        nowTime.day,
                                        nowTime.hour,
                                        nowTime.minute)

if not os.path.exists('experiment_data'):
    os.makedirs('experiment_data')
# create a filename for saving data: subject-date-time-task-run
outputFile = os.path.join('experiment_data',
                          'ambiguous_fade_%s_%s_%s_%s.csv' %(subjInfo['Subject ID'],
                                                       subjInfo['blockType'],
                                                       subjInfo['run #'],
                                                       timeStamp
                                                      ))

####################### Stimulus attributes  
imageSize = 12 # subtense, diameter
imgContrast = 0.0 # before ramp down

# timing info
# cueDuration = 1.
imgDuration = [1., 1.4, 1.8, 2.2, 2.4]
rampDuration = 1.  # measured from participant's button press
promptDelay = [3.] # [1.4, 1.8, 2.2, 2.6, 3.0]
responsePause = [1.5, 2.0, 2.5] # just so people don't feel rushed
nTrials = 15

nBlocks = 1
#blockTypes = ['attn_face', 'attn_house', 'only_face', 'only_house']
imgNumbers = [i for i in range((int(subjInfo['run #'])-1)*nTrials, int(subjInfo['run #'])*nTrials)]
# random.shuffle(imgNumbers)

####################### Monitor set-up
mirroredMonitors = True
localMonitors = monitors.getAllMonitors()
subMonitor = monitors.Monitor('LocalCalibrated') # usually LocalCalibrated
screenSize = subMonitor.getSizePix()
if screenSize is None:
    subMonitor = monitors.Monitor('testMonitor') #
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    print('This computer does not have LocalCalibrated.')
    print('Using testMonitor.')
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
else:
    print('Successfully found LocalCalibrated monitor.')
screenSize=subMonitor.getSizePix()
if mirroredMonitors:
    window = visual.Window(screenSize,
                                        monitor=subMonitor,
                                        units='deg',
                                        screen=1,
                                        color=[0,0,0],
                                        colorSpace='rgb',
                                        fullscr=True, # for Bits# and fMRI we need to mirror
                                        useFBO=True,
                                        allowGUI=True)
else:
    window = visual.Window(screenSize,
                                        monitor=subMonitor,
                                        units='deg',
                                        screen=1,
                                        color=[0,0,0],
                                        colorSpace='rgb',
                                        fullscr=False, # this is the thing that drove us crazy on March 14, 2019
                                        useFBO=True,
                                        allowGUI=True)


img = blended_image(0.5) 
stimImg = visual.GratingStim(window,
                            tex=img,
                            texRes=img.shape, 
                            size=(imageSize),
                            contrast=1.,
                            sf=1./imageSize,
                            units='deg',
                            name='blended')

fixation = visual.Rect(window,
                        size=[0.2,0.2],
                        fillColor=[1,1,1],
                        fillColorSpace='rgb',
                        units='deg')

responseList = []
cognitivePause = 3. # take a 'cognitive pause' at the beginning
timer = core.Clock()

# tell participant what they're looking for
prompt = visual.TextStim(window,
                         text='',
                         pos=(0, 1.5))
if subjInfo['blockType'] == 'attn_face' or subjInfo['blockType'] == 'only_face':
    prompt.text = 'In this block, you will answer the following quesion:\n'\
                + 'What is the gender of the face? (b=female; r=male)\n'\
                + 'Press any button to start block'
elif subjInfo['blockType'] == 'attn_house' or subjInfo['blockType'] == 'only_house':
    prompt.text = 'In this block, you will answer the following quesion:\n'\
                + 'Where is the door of the house? (b=left; r=right)\n'\
                + 'Press any button to start block'
prompt.draw()
window.flip()
wait_for_button_press(responseKeys, timer)
window.flip()

#######################################################################
# and then wait for scanner to send trigger
prompt.text = 'Waiting for trigger ...'

prompt.draw()
fixation.draw()
window.flip()
# HIDE THAT MOUSE!!!
window.setMouseVisible(False)

# start a timer and wait for trigger
wait_for_button_press(triggerKeys, timer)
fixation.draw()
window.flip()
runStartTime = timer.getTime()

blockOnset = timer.getTime()
trialOnset = blockOnset + cognitivePause

for iTrial in range(nTrials):
    # decide on which image to show
    imgNumber = imgNumbers[iTrial]
    if subjInfo['blockType'] == 'attn_face' or subjInfo['blockType'] == 'attn_house':
        face_image, im_face_fileName  = get_image(imgType='face', imgNumber=imgNumber)
        house_image, im_house_fileName = get_image(imgType='house', imgNumber=imgNumber)
        scr_f, _ = get_image(imgType='scrambled_face', imgNumber=imgNumber)
        scr_h, _ = get_image(imgType='scrambled_house', imgNumber=imgNumber)
        img = (face_image+house_image)/2
        scr = (scr_f + scr_h)/np.sqrt(2)
        scr[scr > 1] = 1
        scr[scr < -1] = -1

    elif subjInfo['blockType'] == 'only_face':
        img, im_face_fileName = get_image(imgType='face', imgNumber=imgNumber)
        scr, _ = get_image(imgType='scrambled_face', imgNumber=imgNumber)
    elif subjInfo['blockType'] == 'only_house':
        img, im_face_fileName = get_image(imgType='house', imgNumber=imgNumber)
        scr, _ = get_image(imgType='scrambled_house', imgNumber=imgNumber)
    
    # wait for correct stim onset ... measuring from the last
    while timer.getTime() < trialOnset:
        pass
    trialOnset = timer.getTime()
    
    # put the stimulus up there
    stimImg.tex = img
    stimImg.draw()
    fixation.draw()
    window.flip()
    imgOffset = trialOnset + imgDuration[np.random.randint(len(imgDuration))]
    while timer.getTime() < imgOffset:
        pass
    # wait for a button press
    # imagePercept, imageRT = wait_for_button_press(responseKeys,
    #                                                 timer,
    #                                                 onset_time=stimOnset,
    #                                                 rList=responseList,
    #                                                 oFile=outputFile)
    # start ramp
    nSteps = 100 # seems like enough ...
    rampOnset = timer.getTime()
    t = rampOnset
    while t-rampOnset < rampDuration:
        k = np.sin((t-rampOnset)/rampDuration*np.pi/2)
        blendedImg = (1-k)*img + k*scr
        stimImg.tex = blendedImg
        stimImg.draw()
        fixation.draw()
        window.flip()
        t = timer.getTime()

    noiseOnset = timer.getTime()
    stimImg.tex = scr
    stimImg.draw()
    fixation.draw()
    window.flip()
    # wait a random interval then prompt for percept
    promptOnset = timer.getTime() + promptDelay[np.random.randint(len(promptDelay))]
    prompt.text = 'Press a button to answer the block question.'
    # stimImg.draw()
    prompt.draw()
    while timer.getTime() < promptOnset:
        pass
    window.flip()
    noisePercept, noiseRT = wait_for_button_press(responseKeys,
                                                    timer,
                                                    onset_time=promptOnset,
                                                    rList=responseList,
                                                    oFile=outputFile)
    fixation.draw()
    window.flip()
    # record responses
    responseList.append({'blockType': subjInfo['blockType'],
                 'iTrial': iTrial,
                 'trialOnset': trialOnset,
                 'rampOnset': rampOnset,
                 'noiseOnset': noiseOnset,
                 'promptOnset': promptOnset,
                 'noisePercept': noisePercept,
                 'noiseRT': noiseRT,
                 'im_house_fileName': locals().get('im_house_fileName', None),
                 'im_face_fileName': locals().get('im_face_fileName', None)
                 })
    # plan for next stimulus onset
    trialOnset = timer.getTime() + responsePause[np.random.randint(len(responsePause))]

    print('Saving responses')
    saveResponses(responseList, outputFile)

prompt = visual.TextStim(window,
                         text='Block end',
                         pos=(0, 1.5))
# stimImg.draw()
prompt.draw()
window.flip()
core.wait(5.0)



window.close()
