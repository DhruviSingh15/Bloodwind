from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, SelectField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange, Regexp
from app.models.user import User

class CreateAdminForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Create Admin')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please choose a different one.')


class ManualStockAdjustmentForm(FlaskForm):
    blood_group = StringField('Blood Group', render_kw={'readonly': True})
    current_stock = IntegerField('Current Stock', render_kw={'readonly': True})
    adjustment_type = SelectField('Adjustment Type', 
                                choices=[('add', 'Add Units'), ('deduct', 'Deduct Units')],
                                validators=[DataRequired()])
    units = IntegerField('Units', validators=[DataRequired(), NumberRange(min=1, max=100)])
    reason = TextAreaField('Reason for Adjustment', validators=[DataRequired(), Length(min=5, max=200)])
    submit = SubmitField('Adjust Stock')


class TestSMSForm(FlaskForm):
    phone_number = StringField('Phone Number', validators=[
        DataRequired(),
        Regexp(r'^\+?[1-9]\d{9,14}$', message='Invalid phone number format. Please include country code (e.g., +91XXXXXXXXXX)')
    ])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=5, max=160)])
    submit = SubmitField('Send SMS')
