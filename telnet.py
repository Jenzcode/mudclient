import re

# 0xFF means Interpret As Command
# there are a few IAC codes we need to implement
# Commands that follow 0xFF can be:
# WILL \xFB, WON'T \xFC, DO \xFD, DON'T \xFE
class IAC:
  CAN = re.compile(b'\xFF\xFD\x18')
  DO_MXP = re.compile(b'\xFF\xFD\[')
  DONT_MXP = re.compile(b'\xFF\xFE\[')
  WILL_MXP = re.compile(b'\xFF\xFB\[')
  WONT_MXP = re.compile(b'\xFF\xFC\[')
  WILL_ECHO = re.compile(b'\xFF\xFB\x01')
  WONT_ECHO = re.compile(b'\xFF\xFC\x01')
  list = [      CAN,
                DO_MXP,
                DONT_MXP,
                WILL_MXP,
                WONT_MXP,
                WILL_ECHO,
                WONT_ECHO
        ]

  # Check for and handle IAC codes
  def processIAC(mline):
    result = IAC.CAN.sub(b'IAC_CAN',mline)
    result = IAC.WILL_MXP.sub(b'WILL_MXP',result)
    result = IAC.WONT_MXP.sub(b'WONT_MXP',result)
    result = IAC.WILL_ECHO.sub(b'WILL_ECHO',result)
    result = IAC.WONT_ECHO.sub(b'WONT_ECHO',result)
    return result
