# plans quick

## Urgent

### ui frontend

SOME more images are in the ZALO CLOUD.

#### CFIX ALL BUGS

Manager update status having nonsense Vietnamese., some se pages having vietnamse buttosn
put workflow builder and all the shits (Operation dashboard like customer....)into the sidebar. THe dashboard page should have some stats like Sapo...(doanh thu, don hang moi, tra hang...and some charts)
maager analytic got DENIED with manager????
new page: Seting-for everyone like Store info, Chi nhanh ....(like sapo) and Danh sach don hang (invoice thing). Theme must be consistent.

workflow buiolder: ZOOM mode is useless as hell mount to scrollwheel.Swipeing updownrightup move the whole canva.(LIKE MAKE BRUH)Remove the stupid zoom settngs, and let the mouse do it job.(also we want our workspace to be BIGGER , because our builder is too small it just cut the node. we want it to be as high as infinite if we can.)
workfow builder: when delete clear canvas for some reason the node connection still stay for no reason.
workflow bulder: for some reason padding too low and having tons of issues in nodes. when holding mouse to move at near the corner, the node dont move, but at the middle it work.(basicaly the square node move area is smaller than the node itself)(chủ yếu lỗi là do pixel click vào
tôi để nhỏ hơn ban đầu
nên khi thu nỏ lại thì nó cx bị nhỏ lại)
ưoửflowwo builder : deleting connecting lines is too difficult. Need a better ways to delete nodes properly.
setting page having seveve issue with theme, inconsisetnet and dark light mode issues.No back buttons.
An unexpected error occurred: Unexpected token 'catch' in subcription page.Subcripption page having 100% broken shits

Import page-->add neư button: Fast import-->to Deê learning model

### backend

ocr vision: we can use Paddle OCR (from deep learning as vision)
connnect model-->app api.
connect model-->database of user.DOES ngrok WORK?(Currently we are saving on intergration.py throught Comadb.Memory.py use to MOCK database.)Need to know how much product , stock, best seller,....-->AI agent know. Does NGROK work??? Can it do database? Can we get the api endpoint from website hostinger
a chatbot like chatting in website (popup icon chatbox), sayign like Hello user....In one week your prouct bla bla, would you want me to check bla bla? (the box like a feedback chat/employee chats)
saas.py and some others :currtly in MOCK. Connect to dAABSE!

## Missing feature

Admin like google anaatic: we ONLY need: traffic, revenue(subcription from users they send),keywords common. Fxix new link with google analytic api.
manager/user:must has charts somewheres: tong doanh thu ban hang, don tra don huy, tong so san pham trong ...ngay vua qua, kho...(DATABASE)

# List of Bugs & Issues (MAYBE FIXED?)

Forecast Demand in Product Management is not usable yet (the blue/green button does nothing).

Smart Import (OCR) feature is broken and shows a “failed to fetch” error.

In Create Import Product, users cannot manually enter the product name (it was auto-fixed to “banh mi”).

(Skipped – no item 4 provided)

Workflow shows a network error when browsing Google Drive (and possibly other actions).

When clicking Run in Workflow, it only shows “Executing workflow” with no success or failure result.

After running for a while, the workflow becomes extremely slow and freezes; users cannot continue, cancel, or return to the previous task.

Auto Import in the new template is only a placeholder and does not work.

In SE – Auto Import, the Create Automation section uses a JSON Configuration that is too difficult for normal users; it should be simplified.

Saved workflows can be loaded inside the Workflow Builder, but Saved Automations does not show anything on the main menu.

When a user tops up their balance, admin receives no notification, so there is no way to add funds to the user account.

Admin Analytics & Reports are completely placeholders.

In Admin → Manage Subscriptions, clicking the menu always shows the error:
Unexpected token "catch".

In the same section, clicking Send Manual Bank Reconciliation shows the error:
trigger ManualPayout is not defined.

Because of the above issues, Bank Account linking does not work.

Active Managers and Payment History are broken; Manage Subscriptions has serious errors.

In the Business Dashboard, templates are still placeholders.

The Top Up feature in Wallet & Plans feels incorrect — why does the admin need to pay to use their own service?

Since top-up is broken, it is impossible to test or verify the Withdraw Revenue feature (even admin top-ups fail).

Similar to issue #18, it is unclear why admin needs a Manager Upgrade Status — the older version feels more complete than the new one.

In Create User Account (Manager role), Roles & Permissions cannot be used.

Dashboard templates for all three account types are unusable.

Automation Scenarios are unfinished:

Builder page has font/UI bugs

Cannot properly create scenarios

Tutorial button does nothing
