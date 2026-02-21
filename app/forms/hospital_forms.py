from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError

class BloodRequestForm(FlaskForm):
    blood_group = SelectField('Blood Group Needed', 
                             choices=[('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), 
                                     ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-')], 
                             validators=[DataRequired()])
    units = IntegerField('Units Required', validators=[DataRequired(), NumberRange(min=1, max=10)], default=1)
    urgency = SelectField('Urgency Level', 
                         choices=[('normal', 'Normal'), ('urgent', 'Urgent'), ('critical', 'Critical')], 
                         validators=[DataRequired()], default='normal')
    message = TextAreaField('Additional Message for Donors', validators=[Length(max=200)])
    submit = SubmitField('Broadcast Request')


class UpdateHospitalProfileForm(FlaskForm):
    name = StringField('Hospital Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    address = TextAreaField('Address', validators=[DataRequired(), Length(min=5, max=200)])
    pincode = StringField('Pincode', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Update Profile')

    def validate_pincode(self, pincode):
        if not pincode.data.isdigit():
            raise ValidationError('Pincode must contain only numbers')
