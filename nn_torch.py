import pandas as pd
import numpy as np
from feature_utils import FeatureUtils as fu
import torch
from torch.autograd import Variable
TOTAL_DATASET_SIZE = 10887

def norm_arr(array):
    return (array - array.min() - (array.max() - array.min()) / 2) / ((array.max() - array.min()) / 2)

def rmsle(y_pred,y_true):
    return torch.sqrt(torch.mean(torch.pow((torch.log(y_pred + 1) - torch.log(y_true + 1)),2)))

#Reading datasets
df = pd.read_csv('data/train.csv')
df_to_predict = pd.read_csv('data/test.csv')

#Adding continous time as variable because of the increasing amount of bikes over time
df['cont_time'] = df.datetime.apply(fu.datetime_to_total_hours)
df_to_predict['cont_time'] = df_to_predict.datetime.apply(fu.datetime_to_total_hours)

#Adding hour temporarily
df['hour'] = df.datetime.apply(fu.get_hour)
df_to_predict['hour'] = df_to_predict.datetime.apply(fu.get_hour)

#Little refactor of humidity to make it easier to learn
fu.humidity_impact = np.array(df.groupby('humidity')['count'].mean())

#Month
df['month'] = df.datetime.apply(fu.get_month)

#Getting month impact, which tells us how good is the month for bikes, far better than 'season' and is easier to learn than pure month value
fu.months_impact = np.array(df.groupby('month')['count'].mean())
df['month_impact'] = df.datetime.apply(fu.get_month_impact)
df_to_predict['month_impact'] = df_to_predict.datetime.apply(fu.get_month_impact)

#Year
df['year'] = df.datetime.apply(fu.get_year)
df_to_predict['year'] = df_to_predict.datetime.apply(fu.get_year)

#Day of week
df['day_of_week'] = df.datetime.apply(fu.get_day_of_week)
df_to_predict['day_of_week'] = df_to_predict.datetime.apply(fu.get_day_of_week)

#DAY OF WEEK REG/CAS
fu.days_of_week_reg = np.array(df.groupby('day_of_week')['registered'].mean())
fu.days_of_week_cas = np.array(df.groupby('day_of_week')['casual'].mean())
df['day_of_week_reg'] = df.day_of_week.apply(fu.get_day_of_week_reg)
df['day_of_week_cas'] = df.day_of_week.apply(fu.get_day_of_week_cas)
df_to_predict['day_of_week_reg'] = df_to_predict.day_of_week.apply(fu.get_day_of_week_reg)
df_to_predict['day_of_week_cas'] = df_to_predict.day_of_week.apply(fu.get_day_of_week_cas)

#Hour impact array
fu.hours_impact = np.array(df.groupby('hour')['count'].mean())

#Hour impact arrays for registered and casual
fu.hours_cas = np.array(df.groupby('hour')['casual'].mean())
fu.hours_reg = np.array(df.groupby('hour')['registered'].mean())

#Hour impact arrays for workingday, freeday, sat, sun
fu.hours_workday = norm_arr(df.loc[df['workingday'] == 1].groupby('hour')['count'].mean())
fu.hours_freeday = norm_arr(df.loc[(df['workingday'] == 0) & (df['day_of_week'] < 5)].groupby('hour')['count'].mean())
fu.hours_sat = norm_arr(df.loc[df['day_of_week'] == 5].groupby('hour')['count'].mean())
fu.hours_sun = norm_arr(df.loc[df['day_of_week'] == 6].groupby('hour')['count'].mean())

#Hour impact for registered and casual
df['hour_reg'] = df.datetime.apply(fu.get_hour_registered)
df['hour_cas'] = df.datetime.apply(fu.get_hour_casual)
df_to_predict['hour_reg'] = df_to_predict.datetime.apply(fu.get_hour_registered)
df_to_predict['hour_cas'] = df_to_predict.datetime.apply(fu.get_hour_casual)
#print(df.head(10))

#Data randomization(shuffling)
df = df.sample(frac=1).reset_index(drop=True)
#print(df.head(30))

#Spitting data into input features and labels
datasetY = df.ix[:,'casual':'count']
datasetX = df.drop(['casual','registered','count','datetime','windspeed','atemp','season','month'],1)
datasetX_pred = df_to_predict.drop(['datetime','windspeed','atemp','season'],1)
#print(datasetY.head(10))

#Normalizing inputs
datasetX = (datasetX - datasetX.min() - (datasetX.max() - datasetX.min())/2) / ((datasetX.max() - datasetX.min())/2)
datasetX_pred = (datasetX_pred - datasetX_pred.min() - (datasetX_pred.max() - datasetX_pred.min())/2) / ((datasetX_pred.max() - datasetX_pred.min())/2)

datasetX = datasetX.drop(['day_of_week'],1)
datasetX_pred = datasetX_pred.drop(['day_of_week'],1)

print("Features used:",datasetX.shape)
print("Final train set:",datasetX.head(10))

#Dividing the original train dataset into train/test set, whole set because keras provides spliting to cross-validation and train set
train_setX = datasetX
train_setY = datasetY[['casual','registered','count']].astype(float)

epochs = 50000
train_data_size = 1000
layer_dims = {"in": 13, "fc1": 10, "fc2": 10, "fc3": 10,"fc4": 10, "out": 3}

#Conversion from DF to numpyarray
X_train = np.array(train_setX[:train_data_size])
Y_train = np.array(train_setY[:train_data_size])
print(train_setX.shape)

# Create random Tensors to hold inputs and outputs, and wrap them in Variables.
X_train = Variable(torch.Tensor(X_train))
Y_train = Variable(torch.Tensor(Y_train))
#y = Variable(torch.randn(N, D_out), requires_grad=False)

# Use the nn package to define our model and loss function.
model = torch.nn.Sequential(
    torch.nn.Linear(layer_dims["in"], layer_dims["fc1"]),
    torch.nn.Tanh(),
    torch.nn.Linear(layer_dims['fc1'],layer_dims['fc2']),
    torch.nn.Tanh(),
    torch.nn.Linear(layer_dims['fc2'],layer_dims['fc3']),
    torch.nn.Tanh(),
    torch.nn.Linear(layer_dims['fc3'],layer_dims['fc4']),
    torch.nn.Tanh(),
    torch.nn.Linear(layer_dims['fc4'],layer_dims['out'],
    torch.nn.ReLU())
)

# Use the optim package to define an Optimizer that will update the weights of
# the model for us. Here we will use Adam; the optim package contains many other
# optimization algoriths. The first argument to the Adam constructor tells the
# optimizer which Variables it should update.
learning_rate = 1e-4
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

for t in range(epochs):
    # Forward pass: compute predicted y by passing x to the model.
    y_pred = model(X_train)

    # Compute and print loss.
    loss = rmsle(y_pred, Y_train)
    print(t, loss.data[0])

    # Before the backward pass, use the optimizer object to zero all of the
    # gradients for the variables it will update (which are the learnable weights
    # of the model)
    optimizer.zero_grad()

    # Backward pass: compute gradient of the loss with respect to model
    # parameters
    loss.backward()

    # Calling the step function on an Optimizer makes an update to its
    # parameters
    optimizer.step()