
import pandas as pd
import numpy as np
import string
from string import digits
import matplotlib.pyplot as plt
import re
from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split
from tensorflow.keras.layers import Input, LSTM, Embedding, Dense
from tensorflow.keras.models import Model


# Settings
TRAIN_MODEL = False
TEST_MODEL = True # test mode
# If you don't truncate sequences up to a reasonable maximum, the internal dimensions of your model will be too large
MAX_SEQ_LENGTH = 32 # very important to truncate or things will get too large and bog down the system
latent_dim = 50 # Dimension of latent context vector between encoder and decoder
LOAD_MODEL = True # load a previously trained model to continue training from a checkpoint? - ModelToLoad
ModelToLoad = 'trained_models/TrainedModel06_32maxw_110epochs.h5'

# Determine data to use:
# if TRAIN_MODEL: # you have to analyze the text again for dictionary, etc
# SMALLER TRAIN SET:
# lines= pd.read_table('../input/dataset-twi/en-tw.txt', names=['eng', 'twi'])
# BIGGER TRAIN SET:
lines= pd.read_table('../input/datasetentwi/en-twi.txt', names=['eng', 'twi'])

if TEST_MODEL:
    lines_tw = pd.read_csv('../data/Twi_text.csv',header=None)
    lines_eng = pd.read_csv('../data/English_text.csv',header=None)
    lines_TEST = pd.DataFrame(columns=['eng','twi','twi_predicted'])
    lines_TEST['eng'] = lines_eng[0].tolist()
    lines_TEST['twi'] = lines_tw[0].tolist()


# check dimensions
print('shape of data:')
print(lines.shape)

# Remove all numbers from text
remove_digits = str.maketrans('', '', digits)
lines.eng=lines.eng.apply(lambda x: x.translate(remove_digits))
lines.twi=lines.twi.apply(lambda x: x.translate(remove_digits))
#lines.twi = lines.twi.apply(lambda x: re.sub("[ƆɔɛƐ]", "", x))


# Remove extra spaces
lines.eng=lines.eng.apply(lambda x: x.strip())
lines.twi=lines.twi.apply(lambda x: x.strip())
lines.eng=lines.eng.apply(lambda x: re.sub(" +", " ", x))
lines.twi=lines.twi.apply(lambda x: re.sub(" +", " ", x))


# truncate to MAX_SEQ_LENGTH
lines.eng=lines.eng.apply(lambda x: " ".join(x.split(' ')[:MAX_SEQ_LENGTH]))
lines.twi=lines.twi.apply(lambda x: " ".join(x.split(' ')[:MAX_SEQ_LENGTH]))


# Add start and end tokens to target sequences
lines.twi=lines.twi.apply(lambda x : 'START_ '+ x + ' _END')

# do everything for the _TEST sentences as well
lines_TEST.eng=lines_TEST.eng.apply(lambda x: x.translate(remove_digits))
lines_TEST.twi=lines_TEST.twi.apply(lambda x: x.translate(remove_digits))
lines_TEST.eng=lines_TEST.eng.apply(lambda x: x.strip())
lines_TEST.twi=lines_TEST.twi.apply(lambda x: x.strip())
lines_TEST.eng=lines_TEST.eng.apply(lambda x: re.sub(" +", " ", x))
lines_TEST.twi=lines_TEST.twi.apply(lambda x: re.sub(" +", " ", x))
lines_TEST.eng=lines_TEST.eng.apply(lambda x: " ".join(x.split(' ')[:MAX_SEQ_LENGTH]))
lines_TEST.twi=lines_TEST.twi.apply(lambda x: " ".join(x.split(' ')[:MAX_SEQ_LENGTH]))

lines_TEST.eng=lines_TEST.eng.apply(lambda x: re.sub(r'[^\w\s]','',x))
lines_TEST.twi=lines_TEST.twi.apply(lambda x: re.sub(r'[^\w\s]','',x))

lines_TEST.twi=lines_TEST.twi.apply(lambda x : 'START_ '+ x + ' _END')


# Print a random sample of the data
print("random training data sample:")
print(lines.sample(10))

if TEST_MODEL:
    print("random training data sample:")
    print(lines_TEST.sample(10))


# Vocabulary of English
all_eng_words=set()
for eng in lines.eng:
    for word in eng.split():
        if word not in all_eng_words:
            all_eng_words.add(word)

# Vocabulary of Twi 
all_twi_words=set()
for twi in lines.twi:
    for word in twi.split():
        if word not in all_twi_words:
            all_twi_words.add(word)


# Max Length of source sequence
lenght_list=[]
for l in lines.eng:
    lenght_list.append(len(l.split(' ')))
max_length_src = np.max(lenght_list)


# Max Length of target sequence
lenght_list=[]
for l in lines.twi:
    lenght_list.append(len(l.split(' ')))
max_length_tar = np.max(lenght_list)
max_length_tar

# Missing comments...
input_words = sorted(list(all_eng_words))
target_words = sorted(list(all_twi_words))
num_encoder_tokens = len(all_eng_words)
num_decoder_tokens = len(all_twi_words)
num_encoder_tokens, num_decoder_tokens


# Missing comments...

num_decoder_tokens += 1 # For zero padding
num_decoder_tokens


input_token_index = dict([(word, i+1) for i, word in enumerate(input_words)])
target_token_index = dict([(word, i+1) for i, word in enumerate(target_words)])

reverse_input_char_index = dict((i, word) for word, i in input_token_index.items())
reverse_target_char_index = dict((i, word) for word, i in target_token_index.items())


lines = shuffle(lines)
lines.head(10)

#if TRAIN_MODEL:
# Train - Test Split
X, y = lines.eng, lines.twi
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.1)

# If you wanted to save the data in pickled format:
#X_train.to_pickle('X_train.pkl')
#X_test.to_pickle('X_test.pkl')
    
if TEST_MODEL:
    X_TEST, y_TEST = lines_TEST.eng, lines_TEST.twi


# data generator for training
def generate_batch(X = X_train, y = y_train, batch_size = 16):
    ''' Generate a batch of data '''
    while True:
        for j in range(0, len(X), batch_size):
            encoder_input_data = np.zeros((batch_size, max_length_src),dtype='float32')
            decoder_input_data = np.zeros((batch_size, max_length_tar),dtype='float32')
            decoder_target_data = np.zeros((batch_size, max_length_tar, num_decoder_tokens),dtype='float32')
            for i, (input_text, target_text) in enumerate(zip(X[j:j+batch_size], y[j:j+batch_size])):
                for t, word in enumerate(input_text.split()):
                    encoder_input_data[i, t] = input_token_index[word] # encoder input seq
                for t, word in enumerate(target_text.split()):
                    if t<len(target_text.split())-1:
                        decoder_input_data[i, t] = target_token_index[word] # decoder input seq
                    if t>0:
                        # decoder target sequence (one hot encoded)
                        # does not include the START_ token
                        # Offset by one timestep
                        decoder_target_data[i, t - 1, target_token_index[word]] = 1.
            yield([encoder_input_data, decoder_input_data], decoder_target_data)
            
# data generator for training
def generate_batch_TEST(X = X_TEST, y = y_TEST, batch_size = 16):
    ''' Generate a batch of data '''
    while True:
        for j in range(0, len(X), batch_size):
            encoder_input_data = np.zeros((batch_size, max_length_src),dtype='float32')
            decoder_input_data = np.zeros((batch_size, max_length_tar),dtype='float32')
            decoder_target_data = np.zeros((batch_size, max_length_tar, num_decoder_tokens),dtype='float32')
            for i, (input_text, target_text) in enumerate(zip(X[j:j+batch_size], y[j:j+batch_size])):
                for t, word in enumerate(input_text.split()):
                    encoder_input_data[i, t] = input_token_index[word] # encoder input seq
                    
            yield([encoder_input_data, decoder_input_data], decoder_target_data)


# Encoder
encoder_inputs = Input(shape=(None,))
enc_emb =  Embedding(num_encoder_tokens+1, latent_dim, mask_zero = True,name="state",input_length=1)(encoder_inputs)
encoder_lstm = LSTM(latent_dim, return_state=True)
encoder_outputs, state_h, state_c = encoder_lstm(enc_emb)
# We discard `encoder_outputs` and only keep the states.
encoder_states = [state_h, state_c]


# Set up the decoder, using `encoder_states` as initial state.
decoder_inputs = Input(shape=(None,))
dec_emb_layer = Embedding(num_decoder_tokens+1, latent_dim, mask_zero = True,name="dstate",input_length=1)
dec_emb = dec_emb_layer(decoder_inputs)
# We set up our decoder to return full output sequences,
# and to return internal states as well. We don't use the
# return states in the training model, but we will use them in inference.
decoder_lstm = LSTM(latent_dim, return_sequences=True, return_state=True)
decoder_outputs, _, _ = decoder_lstm(dec_emb,
                                     initial_state=encoder_states)
decoder_dense = Dense(num_decoder_tokens, activation='softmax')
decoder_outputs = decoder_dense(decoder_outputs)

# Define the model that will turn
# `encoder_input_data` & `decoder_input_data` into `decoder_target_data`
model = Model([encoder_inputs, decoder_inputs], decoder_outputs)


# compile model
#model.compile(optimizer='rmsprop', loss='categorical_crossentropy', metrics=['acc'])
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['acc'])

if LOAD_MODEL:
    model.load_weights(ModelToLoad)

if TRAIN_MODEL:
    # Specify training parameters
    train_samples = len(X_train)
    val_samples = len(X_test)
    batch_size = 96 # 32 works, 64 too large on kaggle
    epochs = 5 # 50 for full length run, 2 for short run to make sure things work
    
    
    # Train
    model.fit_generator(generator = generate_batch(X_train, y_train, batch_size = batch_size),
                        steps_per_epoch = train_samples//batch_size,
                        epochs=epochs,
                        validation_data = generate_batch(X_test, y_test, batch_size = batch_size),
                        validation_steps = val_samples//batch_size)
    
    
    # Always save model!!
    model.save('TrainedModel.h5')


# THE FOLLOWING CODE ALLOWS YOU TO MAKE INFERENCE

# Encode the input sequence to get the "thought vectors"
encoder_model = Model(encoder_inputs, encoder_states)

# Decoder setup
# Below tensors will hold the states of the previous time step
decoder_state_input_h = Input(shape=(latent_dim,))
decoder_state_input_c = Input(shape=(latent_dim,))
decoder_states_inputs = [decoder_state_input_h, decoder_state_input_c]

dec_emb2= dec_emb_layer(decoder_inputs) # Get the embeddings of the decoder sequence

# To predict the next word in the sequence, set the initial states to the states from the previous time step
decoder_outputs2, state_h2, state_c2 = decoder_lstm(dec_emb2, initial_state=decoder_states_inputs)
decoder_states2 = [state_h2, state_c2]
decoder_outputs2 = decoder_dense(decoder_outputs2) # A dense softmax layer to generate prob dist. over the target vocabulary

# Final decoder model
decoder_model = Model(
    [decoder_inputs] + decoder_states_inputs,
    [decoder_outputs2] + decoder_states2)


# Decode sequence function
def decode_sequence(input_seq):
    # Encode the input as state vectors.
    states_value = encoder_model.predict(input_seq)
    # Generate empty target sequence of length 1.
    target_seq = np.zeros((1,1))
    # Populate the first character of target sequence with the start character.
    target_seq[0, 0] = target_token_index['START_']

    # Sampling loop for a batch of sequences
    # (to simplify, here we assume a batch of size 1).
    stop_condition = False
    decoded_sentence = ''
    while not stop_condition:
        output_tokens, h, c = decoder_model.predict([target_seq] + states_value)

        # Sample a token
        sampled_token_index = np.argmax(output_tokens[0, -1, :])
        sampled_char = reverse_target_char_index[sampled_token_index]
        decoded_sentence += ' '+sampled_char

        # Exit condition: either hit max length
        # or find stop character.
        if (sampled_char == '_END' or
           len(decoded_sentence) > 50):
            stop_condition = True

        # Update the target sequence (of length 1).
        target_seq = np.zeros((1,1))
        target_seq[0, 0] = sampled_token_index

        # Update states
        states_value = [h, c]

    return decoded_sentence

# Predict several samples to test model - should do this per major checkpoint at some point
if TRAIN_MODEL:
    # Define function to pull sentence from Train queue
    train_gen = generate_batch(X_train, y_train, batch_size = 1)
    k=-1
    
    
    # Evaluate on first sentence
    k+=1
    (input_seq, actual_output), _ = next(train_gen)
    decoded_sentence = decode_sequence(input_seq)
    print('Input English sentence:', X_train[k:k+1].values[0])
    print('Actual Twi Translation:', y_train[k:k+1].values[0][6:-4])
    print('Predicted Twi Translation:', decoded_sentence[:-4])
    
    # Evaluate on first sentence
    k+=1
    (input_seq, actual_output), _ = next(train_gen)
    decoded_sentence = decode_sequence(input_seq)
    print('Input English sentence:', X_train[k:k+1].values[0])
    print('Actual Twi Translation:', y_train[k:k+1].values[0][6:-4])
    print('Predicted Twi Translation:', decoded_sentence[:-4])
    
    # Evaluate on 2nd sentence
    k+=1
    (input_seq, actual_output), _ = next(train_gen)
    decoded_sentence = decode_sequence(input_seq)
    print('Input English sentence:', X_train[k:k+1].values[0])
    print('Actual Twi Translation:', y_train[k:k+1].values[0][6:-4])
    print('Predicted Twi Translation:', decoded_sentence[:-4])
    
    # Evaluate on 3rd sentence
    k+=1
    (input_seq, actual_output), _ = next(train_gen)
    decoded_sentence = decode_sequence(input_seq)
    print('Input English sentence:', X_train[k:k+1].values[0])
    print('Actual Twi Translation:', y_train[k:k+1].values[0][6:-4])
    print('Predicted Twi Translation:', decoded_sentence[:-4])
    
    # Evaluate on 4th sentence
    k+=1
    (input_seq, actual_output), _ = next(train_gen)
    decoded_sentence = decode_sequence(input_seq)
    print('Input English sentence:', X_train[k:k+1].values[0])
    print('Actual Twi Translation:', y_train[k:k+1].values[0][6:-4])
    print('Predicted Twi Translation:', decoded_sentence[:-4])
    
    # Evaluate on 5th sentence
    k+=1
    (input_seq, actual_output), _ = next(train_gen)
    decoded_sentence = decode_sequence(input_seq)
    print('Input English sentence:', X_train[k:k+1].values[0])
    print('Actual Twi Translation:', y_train[k:k+1].values[0][6:-4])
    print('Predicted Twi Translation:', decoded_sentence[:-4])
    
    # Evaluate on 6th sentence
    k+=1
    (input_seq, actual_output), _ = next(train_gen)
    decoded_sentence = decode_sequence(input_seq)
    print('Input English sentence:', X_train[k:k+1].values[0])
    print('Actual Twi Translation:', y_train[k:k+1].values[0][6:-4])
    print('Predicted Twi Translation:', decoded_sentence[:-4])
    
    # Evaluate on 7th sentence
    k+=1
    (input_seq, actual_output), _ = next(train_gen)
    decoded_sentence = decode_sequence(input_seq)
    print('Input English sentence:', X_train[k:k+1].values[0])
    print('Actual Twi Translation:', y_train[k:k+1].values[0][6:-4])
    print('Predicted Twi Translation:', decoded_sentence[:-4])
    
    # Evaluate on 8th sentence
    k+=1
    (input_seq, actual_output), _ = next(train_gen)
    decoded_sentence = decode_sequence(input_seq)
    print('Input English sentence:', X_train[k:k+1].values[0])
    print('Actual Twi Translation:', y_train[k:k+1].values[0][6:-4])
    print('Predicted Twi Translation:', decoded_sentence[:-4])
    
    # Evaluate on 9th sentence
    k+=1
    (input_seq, actual_output), _ = next(train_gen)
    decoded_sentence = decode_sequence(input_seq)
    print('Input English sentence:', X_train[k:k+1].values[0])
    print('Actual Twi Translation:', y_train[k:k+1].values[0][6:-4])
    print('Predicted Twi Translation:', decoded_sentence[:-4])
    
    # Evaluate on 10th sentence
    k+=1
    (input_seq, actual_output), _ = next(train_gen)
    decoded_sentence = decode_sequence(input_seq)
    print('Input English sentence:', X_train[k:k+1].values[0])
    print('Actual Twi Translation:', y_train[k:k+1].values[0][6:-4])
    print('Predicted Twi Translation:', decoded_sentence[:-4])

if TEST_MODEL:
    predicted_translations = []
    # Define function to pull sentence from TEST queue
    TEST_gen = generate_batch_TEST(X_TEST, y_TEST, batch_size = 1)
    k=-1
    for twi_sentence in X_TEST:
        try:
            # Evaluate on next sentence
            k+=1
            (input_seq, actual_output), _ = next(TEST_gen)
            decoded_sentence = decode_sequence(input_seq)
            print('Input English sentence:', X_TEST[k:k+1].values[0])
            print('Actual Twi Translation:', y_TEST[k:k+1].values[0][6:-4])
            print('Predicted Twi Translation:', decoded_sentence[:-4])
            predicted_translations.append(decoded_sentence[:-4])
        except Exception as e:
            print('Translation Failed, probably due to out of vocab words, exact error:')
            print(e)
            predicted_translations.append(str(e))
    lines_TEST['twi_predicted'] = predicted_translations
    lines_TEST.to_csv('../data/Twi_text_predicted.csv')
    
    
        