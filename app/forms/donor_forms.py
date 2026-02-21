from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange, Email, ValidationError
from flask_login import current_user
from app.models.user import User

class DonationRequestForm(FlaskForm):
    hospital_id = SelectField('Select Hospital', coerce=int, validators=[DataRequired()])
    units = IntegerField('Units to Donate', validators=[DataRequired(), NumberRange(min=1, max=2)], default=1)
    notes = TextAreaField('Additional Notes', validators=[Length(max=200)])
    submit = SubmitField('Submit Request')


class UpdateProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    age = IntegerField('Age', validators=[DataRequired(), NumberRange(min=16, max=100)])
    gender = SelectField('Gender', choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], validators=[DataRequired()])
    weight = FloatField('Weight (kg)', validators=[DataRequired(), NumberRange(min=45)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    address = TextAreaField('Address', validators=[DataRequired(), Length(min=5, max=200)])
    pincode = StringField('Pincode', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Update Profile')

    def validate_pincode(self, pincode):
        if not pincode.data.isdigit():
            raise ValidationError('Pincode must contain only numbers')
